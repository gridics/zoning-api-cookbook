using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

public static class GridicsCookbook
{
    static readonly string Root = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(typeof(GridicsCookbook).Assembly.Location) ?? ".", "../../../../"));
    static readonly HttpClient Client = new() { Timeout = TimeSpan.FromSeconds(20) };

    static string FindRoot()
    {
        var current = Directory.GetCurrentDirectory();
        while (current is not null && !File.Exists(Path.Combine(current, "recipes", "manifest.json"))) current = Directory.GetParent(current)?.FullName;
        return current ?? Root;
    }

    static void Dotenv(string root)
    {
        var path = Path.Combine(root, ".env"); if (!File.Exists(path)) return;
        foreach (var raw in File.ReadAllLines(path)) { var line=raw.Trim(); if(line.Length==0||line.StartsWith('#')||!line.Contains('='))continue; var pair=line.Split('=',2); if(Environment.GetEnvironmentVariable(pair[0].Trim()) is null) Environment.SetEnvironmentVariable(pair[0].Trim(),pair[1].Trim().Trim('"','\'')); }
    }

    static JsonNode? Substitute(JsonNode? value, Dictionary<string,string> variables)
    {
        if (value is JsonValue scalar && scalar.TryGetValue<string>(out var text)) return Regex.Replace(text, @"\$\{([A-Z0-9_]+)\}", match => variables.GetValueOrDefault(match.Groups[1].Value, match.Value));
        if (value is JsonArray array) { var result=new JsonArray(); foreach(var item in array) if(item is not null) result.Add(Substitute(item,variables)); return result; }
        if (value is JsonObject obj) { var result=new JsonObject(); foreach(var pair in obj) if(pair.Value is not null) result[pair.Key]=Substitute(pair.Value,variables); return result; }
        return value?.DeepClone();
    }

    static string ErrorMessage(int status, JsonNode? payload)
    {
        var messages=payload?["messages"]?.AsArray().Select(x=>x?.ToString()).Where(x=>x is not null); var detail=messages is null?"request failed":string.Join("; ",messages!);
        var hints=new Dictionary<int,string>{{401,"check GRIDICS_API_KEY"},{403,"check plan, capability, and county entitlement"},{404,"not found or hidden outside entitled scope"},{409,"ambiguous locator"},{422,"invalid request fields or IDs"},{429,"rate, quota, or spending control reached"},{502,"temporary upstream failure"},{503,"temporary authorization, catalog, usage, or release failure"}};
        return $"HTTP {status}: {detail}. {hints.GetValueOrDefault(status,"inspect the redacted request ID")}";
    }

    static async Task<JsonObject> RequestAsync(string baseUrl,string apiKey,JsonObject step,bool dry)
    {
        var path=step["path"]!.ToString(); var query=step["query"] as JsonObject; if(query is not null&&query.Count>0) path+="?"+string.Join("&",query.Select(x=>$"{Uri.EscapeDataString(x.Key)}={Uri.EscapeDataString(x.Value!.ToString())}")); var url=baseUrl.TrimEnd('/')+path;
        if(dry) return new JsonObject{{"name",step["name"]!.ToString()},{"status","dry_run"},{"request",new JsonObject{{"method",step["method"]!.ToString()},{"url",url},{"headers",new JsonObject{{"x-api-key","[REDACTED]"}}},{"body",step["body"]?.DeepClone()}}}};
        JsonObject? last=null;
        for(var attempt=1;attempt<=(step["max_attempts"]?.GetValue<int>()??3);attempt++){
            try { using var request=new HttpRequestMessage(new HttpMethod(step["method"]!.ToString()),url); request.Headers.Add("x-api-key",apiKey); request.Headers.Add("Accept","application/json"); request.Headers.Add("User-Agent","zoning-api-cookbook/csharp"); if(step["body"] is not null) request.Content=new StringContent(step["body"]!.ToJsonString(),Encoding.UTF8,"application/json"); using var response=await Client.SendAsync(request); var raw=await response.Content.ReadAsStringAsync(); JsonNode? payload; try{payload=JsonNode.Parse(string.IsNullOrWhiteSpace(raw)?"{}":raw);}catch{payload=new JsonObject{{"status","ERROR"},{"messages",new JsonArray("non-JSON response")}};} if(response.IsSuccessStatusCode)return new JsonObject{{"name",step["name"]!.ToString()},{"status","ok"},{"http_status",(int)response.StatusCode},{"request_id",response.Headers.TryGetValues("x-request-id",out var values)?values.FirstOrDefault():null},{"data",payload}}; var status=(int)response.StatusCode; last=new JsonObject{{"name",step["name"]!.ToString()},{"status","error"},{"http_status",status},{"error",ErrorMessage(status,payload)},{"data",payload}}; if(status is not (429 or 502 or 503))return last; }
            catch(Exception error){last=new JsonObject{{"name",step["name"]!.ToString()},{"status","error"},{"http_status",null},{"error","network error: "+error.Message}};}
            if(attempt<(step["max_attempts"]?.GetValue<int>()??3))await Task.Delay(250*(1<<(attempt-1)));
        } return last!;
    }

    static JsonObject? LocationStep(JsonObject step, JsonArray results, Dictionary<string,string> vars, string session) {
        var mode=vars["GRIDICS_LOCATION_MODE"];if(mode=="forward"&&step["name"]!.ToString()!="suggest_1")return null;
        var query=new JsonObject{{"q",vars["GRIDICS_LOCATION_QUERY"]},{"limit",vars["GRIDICS_LOCATION_LIMIT"]}};
        foreach(var key in new[]{"country","language","proximity","bbox"})if(vars["GRIDICS_LOCATION_"+key.ToUpperInvariant()]!="")query[key]=vars["GRIDICS_LOCATION_"+key.ToUpperInvariant()];
        step["max_attempts"]=1;
        if(mode=="forward"){step["name"]="forward";step["path"]="/v2/locations/forward";}
        else if(step["name"]!.ToString()=="retrieve"){var suggestions=results.LastOrDefault()?["data"]?["suggestions"] as JsonArray;if(suggestions is null||suggestions.Count==0)return null;step["path"]="/v2/locations/retrieve/"+Uri.EscapeDataString(suggestions[0]!["gridics_id"]!.ToString());query=new JsonObject{{"session_token",session}};}
        else query["session_token"]=session;
        step["query"]=query;return step;
    }
    static JsonObject LocationReport(JsonArray results) {
        JsonArray suggestions=new(),features=new(),provenance=new();bool failed=false;
        foreach(var item in results){var name=item!["name"]!.ToString();if(name.StartsWith("suggest"))suggestions=item["data"]?["suggestions"]?.DeepClone() as JsonArray??new();if(name is "retrieve" or "forward")features=item["data"]?["features"]?.DeepClone() as JsonArray??new();if(item["status"]!.ToString()=="error")failed=true;provenance.Add(new JsonObject{{"step",name},{"status",item["status"]!.ToString()},{"request_id",(item["request_id"]??item["data"]?["response_id"])?.DeepClone()}});}
        return new JsonObject{{"kind","location_search"},{"session_token",results.FirstOrDefault()?["session_token"]?.DeepClone()},{"mode",results.FirstOrDefault()?["name"]?.ToString()=="forward"?"forward":"suggest_retrieve"},{"suggestions",suggestions},{"features",features},{"state",failed?"error":features.Count>1?"ambiguous":suggestions.Count+features.Count>0?"resolved":"no_match"},{"provenance",provenance}};
    }
    static JsonObject AppraiserStep(JsonObject step, JsonArray results, Dictionary<string,string> vars) {
        step["max_attempts"]=1;
        if(step["name"]!.ToString()=="property") {
            var locator=Environment.GetEnvironmentVariable("GRIDICS_LOCATOR")??"address";
            if(locator!="address"&&locator!="apn"&&locator!="parcel_id")throw new ArgumentException("GRIDICS_LOCATOR must be address, apn or parcel_id");
            if(locator!="address"){var body=step["body"]!.AsObject();body.Remove("address");body[locator]=vars[locator=="apn"?"GRIDICS_APN":"GRIDICS_PARCEL_ID"];}
        }else if(step["name"]!.ToString()=="zoning"&&results.Count>0&&results[0]?["status"]?.ToString()=="ok") {
            var subject=results[0]!["data"]!["data"]!;var markets=subject["market_ids"] as JsonArray;
            if(subject["id"] is null||subject["place_id"] is null||markets?.Count!=1)throw new ArgumentException("Lookup did not establish one canonical parcel/Place/Market; clarify before zoning");
            step["body"]=new JsonObject{{"group_id",subject["id"]!.DeepClone()},{"place_id",subject["place_id"]!.DeepClone()},{"market_id",markets[0]!.DeepClone()}};
        }
        return step;
    }
    static JsonObject AppraiserReport(JsonArray results) {
        JsonNode? Data(int i)=>i<results.Count&&results[i]?["status"]?.ToString()=="ok"?results[i]?["data"]?["data"]:null;
        var subject=Data(0);var zoning=Data(1);var fields=subject?["fields"];
        var address=fields?["parcel.address"]??subject?["address"];var apn=fields?["parcel.apn"]??subject?["identifiers"]?["apn"]??subject?["apn"];var code=fields?["zoning.code"]??subject?["zoning_code"];
        var unknowns=new List<string>{"zoning description","development capacity","permitted uses (retrieve separately when authorized)"};
        if(address is null)unknowns.Add("address");if(apn is null)unknowns.Add("APN");if(code is null)unknowns.Add("zoning designation");if((fields?["parcel.lot_area"]??subject?["lot_area"]) is null)unknowns.Add("lot area");
        bool Has(string[] keys)=>(zoning?["buildings"] as JsonArray)?.Any(b=>keys.Any(k=>b?["Envelope"]?[k] is not null))??false;
        if(!Has(["PrincipalMaxHeight","TotalBuildingHeightFeet"]))unknowns.Add("height");
        if(!Has(["EffectivePFrontSetbackPrincipal","EffectivePSideSetback","EffectivePRearSetback"]))unknowns.Add("setbacks");
        if(zoning is null)unknowns.Add("zoning response");
        var provenance=new JsonArray();foreach(var r in results)provenance.Add(new JsonObject{{"step",r?["name"]?.DeepClone()},{"status",r?["status"]?.DeepClone()},{"request_id",(r?["request_id"]??r?["data"]?["meta"]?["request_id"])?.DeepClone()}});
        string Display(JsonNode? v)=>v?.ToString().Replace("\n"," ").Replace("`","")??"unknown";
        var boundary="Factual Gridics data summary; not a formal appraisal, title opinion, legal advice, binding zoning determination or permit assurance.";
        var markdown="# Gridics appraisal subject summary\n\n"+string.Join("\n",new[]{"Address: "+Display(address),"Parcel: "+Display(subject?["id"]),"APN: "+Display(apn),"Zoning designation: "+Display(code),"Request IDs: "+string.Join(", ",provenance.Select(r=>Display(r?["request_id"]))),"Unknown/unavailable: "+string.Join("; ",unknowns),boundary})+"\n";
        return new JsonObject{{"kind","appraiser_zoning"},{"property",subject?.DeepClone()},{"zoning",zoning?.DeepClone()},{"provenance",provenance},{"retrieved_at",DateTimeOffset.UtcNow.ToString("O")},{"unknowns",new JsonArray(unknowns.Select(x=>(JsonNode?)JsonValue.Create(x)).ToArray())},{"professional_boundary",boundary},{"markdown",markdown}};
    }

    static JsonNode? Workflow(string recipeId, JsonArray results)
    {
        JsonNode? Payload(int index) => index<results.Count ? results[index]?["data"]?["data"]?.DeepClone() : null;
        if(recipeId=="06"){var rows=new JsonArray();foreach(var item in results)foreach(var row in item?["data"]?["data"]?.AsArray()??[])rows.Add(row?.DeepClone());return new JsonObject{{"kind","bounded_export"},{"rows",rows},{"row_count",rows.Count},{"pages",results.Count},{"complete",string.IsNullOrEmpty(results.LastOrDefault()?["data"]?["pagination"]?["next_cursor"]?.ToString())}};}
        if(recipeId=="10"){var rows=new JsonArray();for(var index=0;index<results.Count;index++)rows.Add(new JsonObject{{"row_id",$"portfolio-{index+1:000}"},{"status",results[index]?["status"]?.ToString()},{"property",Payload(index)}});return new JsonObject{{"kind","portfolio_enrichment"},{"rows",rows}};}
        if(recipeId=="11"){var blocked=results.Any(item=>item?["status"]?.ToString()=="unavailable");return new JsonObject{{"kind","redevelopment_screen"},{"assessment_status",blocked?"capability_blocked":"review_required"},{"candidates",blocked?new JsonArray():Payload(1)},{"legal_conclusion",false}};}
        if(recipeId=="12")return new JsonObject{{"kind","retail_shortlist"},{"candidates",Payload(1)},{"scoring","customer_defined"},{"excluded_datasets",new JsonArray("demographics","traffic","competitors","drive_times","rent","availability")}};
        if(recipeId=="18")return LocationReport(results);
        if(recipeId=="17")return AppraiserReport(results);
        if(recipeId=="13"){var provenance=new JsonArray();foreach(var item in results)provenance.Add(new JsonObject{{"step",item?["name"]?.ToString()},{"request_id",item?["request_id"]?.ToString()??item?["data"]?["meta"]?["request_id"]?.ToString()}});return new JsonObject{{"kind","property_factsheet"},{"property",Payload(0)},{"zoning",Payload(1)},{"provenance",provenance},{"customer_notes",null}};}
        if(recipeId=="14")return new JsonObject{{"kind","property_snapshot"},{"property",Payload(0)},{"comparison_semantics","observed API response; not an ordinance effective-date record"}};
        if(recipeId=="15"){var property=Payload(0);var zoning=Payload(1);return new JsonObject{{"kind","due_diligence_screen"},{"overall","needs_review"},{"rule_version","example-v1"},{"criteria",new JsonArray(new JsonObject{{"name","property_resolved"},{"status",property is null?"needs_review":"meets"}},new JsonObject{{"name","zoning_available"},{"status",zoning is null?"needs_review":"meets"}})},{"facts",new JsonObject{{"property",property},{"zoning",zoning}}},{"legal_conclusion",false}};}
        return null;
    }

    public static async Task<(int,JsonObject)> ExecuteAsync(string recipeId,JsonObject? overrides=null)
    {
        var root=FindRoot(); Dotenv(root); var manifest=JsonNode.Parse(await File.ReadAllTextAsync(Path.Combine(root,"recipes","manifest.json")))!.AsObject(); var recipe=manifest["recipes"]!.AsArray().FirstOrDefault(x=>x?["id"]?.ToString()==recipeId)?.AsObject(); if(recipe is null)return(2,new JsonObject{{"status","error"},{"error","unknown recipe "+recipeId}});
        var dry=Environment.GetEnvironmentVariable("GRIDICS_DRY_RUN")=="1"; var fixture=Environment.GetEnvironmentVariable("GRIDICS_FIXTURE_MODE")=="1"; var baseUrl=Environment.GetEnvironmentVariable("GRIDICS_API_BASE_URL")??manifest["api"]!["default_base_url"]!.ToString(); var apiKey=Environment.GetEnvironmentVariable("GRIDICS_API_KEY")??""; if(!dry&&apiKey.Length==0)return(2,new JsonObject{{"status","error"},{"error","GRIDICS_API_KEY is required; see README.md#get-an-api-key"}});
        var vars=new Dictionary<string,string>(); foreach(var pair in manifest["defaults"]!.AsObject())vars[pair.Key]=Environment.GetEnvironmentVariable(pair.Key)??pair.Value!.ToString(); var mapping=new Dictionary<string,string>{{"market_id","GRIDICS_MARKET_ID"},{"place_id","GRIDICS_PLACE_ID"},{"parcel_id","GRIDICS_PARCEL_ID"},{"apn","GRIDICS_APN"},{"address","GRIDICS_ADDRESS"},{"postal_code","GRIDICS_POSTAL_CODE"}}; if(overrides is not null)foreach(var pair in overrides)if(pair.Value is not null&&mapping.TryGetValue(pair.Key,out var env))vars[env]=pair.Value.ToString();
        var results=new JsonArray(); var failed=false;
        var locationSession=Guid.NewGuid().ToString();
        foreach(var raw in recipe["steps"]!.AsArray())
        {
            var step=Substitute(raw,vars)!.AsObject();
            if(recipeId=="18"){var next=LocationStep(step,results,vars,locationSession);if(next is null)continue;step=next;}
            if(recipeId=="17"){try{step=AppraiserStep(step,results,vars);}catch(ArgumentException error){results.Add(new JsonObject{{"name",step["name"]!.ToString()},{"status","error"},{"error",error.Message}});failed=true;break;}}
            if(recipeId=="11"&&step["name"]!.ToString()=="candidates"&&!dry){
                var available=(results[0]?["data"]?["data"]?.AsArray()??[]).Any(field=>field?["name"]?.ToString()=="development.max_buildable_area"&&field?["caller_available"]?.GetValue<bool>()==true&&field?["selectable"]?.GetValue<bool>()==true);
                if(!available){results.Add(new JsonObject{{"name","candidates"},{"status","unavailable"},{"http_status",null},{"request_sent",false},{"data",new JsonObject{{"messages",new JsonArray("capacity_fields unavailable")}}}});continue;}
            }
            var result=await RequestAsync(baseUrl,apiKey,step,dry);if(recipeId=="18"&&apiKey!="")result=JsonNode.Parse(result.ToJsonString().Replace(apiKey,"[REDACTED]"))!.AsObject();if(recipeId=="18")result["session_token"]=step["name"]!.ToString()=="forward"?null:locationSession;
            if(result["status"]!.ToString()=="error"){if(step["optional"]?.GetValue<bool>()==true&&(result["http_status"]?.GetValue<int>()==403))result["status"]="unavailable";else failed=true;}
            results.Add(result); if(failed)break;
            if(recipeId=="06"&&result["status"]!.ToString()=="ok"&&!dry)
            {
                var seen=new HashSet<string>(); var cursor=result["data"]?["pagination"]?["next_cursor"]?.ToString(); var rowCount=result["data"]?["data"]?.AsArray().Count??0; var page=1;
                while(!string.IsNullOrEmpty(cursor)&&seen.Add(cursor)&&page<3&&rowCount<100)
                {
                    page++; var next=step.DeepClone().AsObject(); next["name"]=$"page_{page}"; var body=next["body"]?.AsObject(); if(body is null){body=new JsonObject();next["body"]=body;} body["cursor"]=cursor;
                    var nextResult=await RequestAsync(baseUrl,apiKey,next,false); results.Add(nextResult);
                    if(nextResult["status"]!.ToString()!="ok"){failed=true;break;}
                    rowCount+=nextResult["data"]?["data"]?.AsArray().Count??0; cursor=nextResult["data"]?["pagination"]?["next_cursor"]?.ToString();
                }
            }
        }
        var count=results.Count(x=>x?["status"]?.ToString()!="dry_run"&&x?["request_sent"]?.GetValue<bool>()!=false);var output=new JsonObject{{"status",failed?"error":"ok"},{"recipe",recipeId},{"title",recipe["title"]!.ToString()},{"execution",dry?"dry_run":fixture?"fixture":"live"},{"api_base_url",baseUrl},{"request_count",count},{"results",results}};var workflow=Workflow(recipeId,results);if(workflow is not null)output["workflow"]=workflow;return(failed?1:0,output);
    }

    static readonly (string Name,string Description,string Recipe,JsonObject Properties)[] Tools=[
        ("gridics_verify_credential","Verify the server-side Gridics API key","01",new()),
        ("gridics_list_counties","List entitled counties in a Market","02",new(){{"market_id",new JsonObject{{"type","string"}}}}),
        ("gridics_lookup_property","Look up one property","03",new(){{"place_id",new JsonObject{{"type","string"}}},{"address",new JsonObject{{"type","string"}}},{"postal_code",new JsonObject{{"type","string"}}}}),
        ("gridics_search_parcels","Run a bounded county parcel search","05",new(){{"place_id",new JsonObject{{"type","string"}}}}),
        ("gridics_get_zoning","Get zoning for one known parcel","04",new(){{"market_id",new JsonObject{{"type","string"}}},{"place_id",new JsonObject{{"type","string"}}},{"parcel_id",new JsonObject{{"type","string"}}}})
    ];

    static async Task<int> McpAsync()
    {
        string? line;
        while ((line = Console.ReadLine()) is not null)
        {
            var msg = JsonNode.Parse(line)!.AsObject();
            var method = msg["method"]?.ToString();
            if (method == "notifications/initialized") continue;
            var id = msg["id"]?.DeepClone();
            JsonObject response;
            if (method == "initialize")
            {
                response = new JsonObject {
                    {"jsonrpc", "2.0"}, {"id", id},
                    {"result", new JsonObject {
                        {"protocolVersion", "2025-06-18"},
                        {"capabilities", new JsonObject {{"tools", new JsonObject()}}},
                        {"serverInfo", new JsonObject {{"name", "gridics-api-cookbook"}, {"version", "1.0.0"}}}
                    }}
                };
            }
            else if (method == "tools/list")
            {
                var list = new JsonArray();
                foreach (var tool in Tools)
                    list.Add(new JsonObject {
                        {"name", tool.Name}, {"description", tool.Description},
                        {"inputSchema", new JsonObject {{"type", "object"}, {"properties", tool.Properties.DeepClone()}, {"additionalProperties", false}}}
                    });
                response = new JsonObject {{"jsonrpc", "2.0"}, {"id", id}, {"result", new JsonObject {{"tools", list}}}};
            }
            else if (method == "tools/call")
            {
                var name = msg["params"]?["name"]?.ToString();
                var tool = Tools.FirstOrDefault(item => item.Name == name);
                if (tool.Name is null)
                    response = new JsonObject {{"jsonrpc", "2.0"}, {"id", id}, {"error", new JsonObject {{"code", -32602}, {"message", "unknown or disallowed tool"}}}};
                else
                {
                    var (code, output) = await ExecuteAsync(tool.Recipe, msg["params"]?["arguments"] as JsonObject);
                    response = new JsonObject {
                        {"jsonrpc", "2.0"}, {"id", id},
                        {"result", new JsonObject {
                            {"content", new JsonArray(new JsonObject {{"type", "text"}, {"text", output.ToJsonString()}})},
                            {"structuredContent", output}, {"isError", code != 0}
                        }}
                    };
                }
            }
            else response = new JsonObject {{"jsonrpc", "2.0"}, {"id", id}, {"error", new JsonObject {{"code", -32601}, {"message", "method not found"}}}};
            Console.WriteLine(response.ToJsonString());
        }
        return 0;
    }

    public static async Task<int> RunAsync(string recipeId){if(Environment.GetCommandLineArgs().Contains("--mcp"))return await McpAsync();var(code,output)=await ExecuteAsync(recipeId);Console.WriteLine(output.ToJsonString(new JsonSerializerOptions{WriteIndented=true}));return code;}
}
