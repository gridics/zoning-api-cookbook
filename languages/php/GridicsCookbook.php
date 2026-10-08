<?php
declare(strict_types=1);

final class GridicsCookbook
{
    private const TRANSIENT = [429, 502, 503];

    private static function root(): string { return dirname(__DIR__, 2); }

    private static function dotenv(): void
    {
        $file = self::root() . '/.env';
        if (!is_file($file)) return;
        foreach (file($file, FILE_IGNORE_NEW_LINES) ?: [] as $raw) {
            $line = trim($raw);
            if ($line === '' || str_starts_with($line, '#') || !str_contains($line, '=')) continue;
            [$key, $value] = explode('=', $line, 2);
            if (getenv(trim($key)) === false) putenv(trim($key) . '=' . trim(trim($value), "\"'"));
        }
    }

    private static function substitute(mixed $value, array $variables): mixed
    {
        if (is_string($value)) return preg_replace_callback('/\$\{([A-Z0-9_]+)\}/', fn($match) => $variables[$match[1]] ?? $match[0], $value);
        if (is_array($value)) { $result = []; foreach ($value as $key => $item) if ($item !== null) $result[$key] = self::substitute($item, $variables); return $result; }
        return $value;
    }

    private static function errorMessage(int $status, array $payload): string
    {
        $detail = isset($payload['messages']) && is_array($payload['messages']) ? implode('; ', $payload['messages']) : 'request failed';
        $hints = [401=>'check GRIDICS_API_KEY',403=>'check plan, capability, and county entitlement',404=>'not found or hidden outside entitled scope',409=>'ambiguous locator',422=>'invalid request fields or IDs',429=>'rate, quota, or spending control reached',502=>'temporary upstream failure',503=>'temporary authorization, catalog, usage, or release failure'];
        return "HTTP $status: $detail. " . ($hints[$status] ?? 'inspect the redacted request ID');
    }

    private static function request(string $baseUrl, string $key, array $step, bool $dry): array
    {
        $url = rtrim($baseUrl, '/') . $step['path'];
        if (!empty($step['query'])) $url .= '?' . http_build_query($step['query']);
        if ($dry) return ['name'=>$step['name'],'status'=>'dry_run','request'=>['method'=>$step['method'],'url'=>$url,'headers'=>['x-api-key'=>'[REDACTED]']] + (isset($step['body']) ? ['body'=>$step['body']] : [])];
        $last = [];
        for ($attempt = 1; $attempt <= ($step['max_attempts']??3); $attempt++) {
            $headers = ["x-api-key: $key", 'Accept: application/json', 'User-Agent: zoning-api-cookbook/php'];
            $content = '';
            if (isset($step['body'])) { $headers[] = 'Content-Type: application/json'; $content = json_encode($step['body'], JSON_THROW_ON_ERROR); }
            $context = stream_context_create(['http'=>['method'=>$step['method'],'header'=>implode("\r\n", $headers),'content'=>$content,'timeout'=>20,'ignore_errors'=>true]]);
            $raw = @file_get_contents($url, false, $context);
            $responseHeaders = $http_response_header ?? [];
            $status = 0;
            if (isset($responseHeaders[0]) && preg_match('/\s(\d{3})\s/', $responseHeaders[0], $match)) $status = (int)$match[1];
            if ($raw === false && $status === 0) $last = ['name'=>$step['name'],'status'=>'error','http_status'=>null,'error'=>'network error or timeout'];
            else {
                $payload = json_decode($raw ?: '{}', true);
                if (!is_array($payload)) $payload = ['status'=>'ERROR','messages'=>['non-JSON response']];
                if ($status >= 200 && $status < 300) return ['name'=>$step['name'],'status'=>'ok','http_status'=>$status,'data'=>$payload];
                $last = ['name'=>$step['name'],'status'=>'error','http_status'=>$status,'error'=>self::errorMessage($status, $payload),'data'=>$payload];
                if (!in_array($status, self::TRANSIENT, true)) return $last;
            }
            if ($attempt < 3) usleep(250000 * (2 ** ($attempt - 1)));
        }
        return $last;
    }

    private static function locationStep(array $step, array $results, array $vars, string $session): ?array {
        $mode=$vars['GRIDICS_LOCATION_MODE']; if($mode==='forward'&&$step['name']!=='suggest_1')return null;
        $query=['q'=>$vars['GRIDICS_LOCATION_QUERY'],'limit'=>$vars['GRIDICS_LOCATION_LIMIT']];
        foreach(['country','language','proximity','bbox'] as $key)if($vars['GRIDICS_LOCATION_'.strtoupper($key)]!=='')$query[$key]=$vars['GRIDICS_LOCATION_'.strtoupper($key)];
        $step['max_attempts']=1;
        if($mode==='forward'){ $step['name']='forward';$step['path']='/v2/locations/forward'; }
        elseif($step['name']==='retrieve'){ $suggestions=$results[array_key_last($results)]['data']['suggestions']??[];if(!$suggestions)return null;$step['path']='/v2/locations/retrieve/'.rawurlencode($suggestions[0]['gridics_id']);$query=['session_token'=>$session]; }
        else $query['session_token']=$session;
        $step['query']=$query;return $step;
    }
    private static function locationReport(array $results): array {
        $suggestions=[];$features=[];$failed=false;$provenance=[];
        foreach($results as $item){if(str_starts_with($item['name'],'suggest'))$suggestions=$item['data']['suggestions']??[];if(in_array($item['name'],['retrieve','forward']))$features=$item['data']['features']??[];if($item['status']==='error')$failed=true;$provenance[]=['step'=>$item['name'],'status'=>$item['status'],'request_id'=>$item['request_id']??$item['data']['response_id']??null];}
        return ['kind'=>'location_search','session_token'=>$results[0]['session_token']??null,'mode'=>($results[0]['name']??'')==='forward'?'forward':'suggest_retrieve','suggestions'=>$suggestions,'features'=>$features,'state'=>$failed?'error':(count($features)>1?'ambiguous':($suggestions||$features?'resolved':'no_match')),'provenance'=>$provenance];
    }
    private static function appraiserStep(array $step, array $results, array $variables): array {
        $step['max_attempts']=1;
        if($step['name']==='property') {
            $locator=getenv('GRIDICS_LOCATOR')?:'address';
            if(!in_array($locator,['address','apn','parcel_id'],true)) throw new RuntimeException('GRIDICS_LOCATOR must be address, apn or parcel_id');
            if($locator!=='address'){unset($step['body']['address']);$step['body'][$locator]=$variables[$locator==='apn'?'GRIDICS_APN':'GRIDICS_PARCEL_ID'];}
        }elseif($step['name']==='zoning'&&($results[0]['status']??null)==='ok'){
            $subject=$results[0]['data']['data'];$markets=$subject['market_ids']??[];
            if(empty($subject['id'])||empty($subject['place_id'])||count($markets)!==1)throw new RuntimeException('Lookup did not establish one canonical parcel/Place/Market; clarify before zoning');
            $step['body']=['group_id'=>$subject['id'],'place_id'=>$subject['place_id'],'market_id'=>$markets[0]];
        }
        return $step;
    }
    private static function appraiserReport(array $results): array {
        $data=fn($i)=>($results[$i]['status']??null)==='ok'?($results[$i]['data']['data']??null):null;
        $subject=$data(0);$zoning=$data(1);$fields=$subject['fields']??[];
        $address=$fields['parcel.address']??$subject['address']??null;$apn=$fields['parcel.apn']??$subject['identifiers']['apn']??$subject['apn']??null;$code=$fields['zoning.code']??$subject['zoning_code']??null;
        $unknowns=['zoning description','development capacity','permitted uses (retrieve separately when authorized)'];
        if($address===null)$unknowns[]='address';if($apn===null)$unknowns[]='APN';if($code===null)$unknowns[]='zoning designation';if(($fields['parcel.lot_area']??$subject['lot_area']??null)===null)$unknowns[]='lot area';
        $has=function($keys)use($zoning){foreach($zoning['buildings']??[] as $b)foreach($keys as $k)if(($b['Envelope'][$k]??null)!==null)return true;return false;};
        if(!$has(['PrincipalMaxHeight','TotalBuildingHeightFeet']))$unknowns[]='height';
        if(!$has(['EffectivePFrontSetbackPrincipal','EffectivePSideSetback','EffectivePRearSetback']))$unknowns[]='setbacks';
        if($zoning===null)$unknowns[]='zoning response';
        $provenance=array_map(fn($r)=>['step'=>$r['name'],'status'=>$r['status'],'request_id'=>$r['request_id']??$r['data']['meta']['request_id']??null],$results);
        $display=fn($v)=>$v===null?'unknown':str_replace(["\n",'`'],[' ',''],(string)$v);
        $boundary='Factual Gridics data summary; not a formal appraisal, title opinion, legal advice, binding zoning determination or permit assurance.';
        $markdown="# Gridics appraisal subject summary\n\n".implode("\n",['Address: '.$display($address),'Parcel: '.$display($subject['id']??null),'APN: '.$display($apn),'Zoning designation: '.$display($code),'Request IDs: '.implode(', ',array_map(fn($r)=>$display($r['request_id']),$provenance)),'Unknown/unavailable: '.implode('; ',$unknowns),$boundary])."\n";
        return ['kind'=>'appraiser_zoning','property'=>$subject,'zoning'=>$zoning,'provenance'=>$provenance,'retrieved_at'=>gmdate('c'),'unknowns'=>$unknowns,'professional_boundary'=>$boundary,'markdown'=>$markdown];
    }

    private static function workflow(string $recipeId, array $results): ?array
    {
        $payload=fn(int $index)=>$results[$index]['data']['data']??null;
        if($recipeId==='06'){ $rows=[];foreach($results as $item)$rows=array_merge($rows,$item['data']['data']??[]);return['kind'=>'bounded_export','rows'=>$rows,'row_count'=>count($rows),'pages'=>count($results),'complete'=>empty($results[array_key_last($results)]['data']['pagination']['next_cursor'])]; }
        if($recipeId==='10')return['kind'=>'portfolio_enrichment','rows'=>array_map(fn($item,$index)=>['row_id'=>sprintf('portfolio-%03d',$index+1),'status'=>$item['status'],'property'=>$payload($index)],$results,array_keys($results))];
        if($recipeId==='11'){ $blocked=(bool)array_filter($results,fn($item)=>$item['status']==='unavailable');return['kind'=>'redevelopment_screen','assessment_status'=>$blocked?'capability_blocked':'review_required','candidates'=>$blocked?[]:$payload(1),'legal_conclusion'=>false]; }
        if($recipeId==='12')return['kind'=>'retail_shortlist','candidates'=>$payload(1)??[],'scoring'=>'customer_defined','excluded_datasets'=>['demographics','traffic','competitors','drive_times','rent','availability']];
        if($recipeId==='18')return self::locationReport($results);
        if($recipeId==='17')return self::appraiserReport($results);
        if($recipeId==='13')return['kind'=>'property_factsheet','property'=>$payload(0),'zoning'=>$payload(1),'provenance'=>array_map(fn($item)=>['step'=>$item['name'],'request_id'=>$item['request_id']??$item['data']['meta']['request_id']??null],$results),'customer_notes'=>null];
        if($recipeId==='14')return['kind'=>'property_snapshot','property'=>$payload(0),'comparison_semantics'=>'observed API response; not an ordinance effective-date record'];
        if($recipeId==='15'){ $property=$payload(0);$zoning=$payload(1);return['kind'=>'due_diligence_screen','overall'=>'needs_review','rule_version'=>'example-v1','criteria'=>[['name'=>'property_resolved','status'=>$property?'meets':'needs_review'],['name'=>'zoning_available','status'=>$zoning?'meets':'needs_review']],'facts'=>['property'=>$property,'zoning'=>$zoning],'legal_conclusion'=>false]; }
        return null;
    }

    public static function execute(string $recipeId, array $overrides = []): array
    {
        self::dotenv();
        $manifest = json_decode(file_get_contents(self::root() . '/recipes/manifest.json'), true, flags: JSON_THROW_ON_ERROR);
        $recipe = null; foreach ($manifest['recipes'] as $item) if ($item['id'] === $recipeId) $recipe = $item;
        if ($recipe === null) return [2, ['status'=>'error','error'=>"unknown recipe $recipeId"]];
        $dry = getenv('GRIDICS_DRY_RUN') === '1'; $fixture = getenv('GRIDICS_FIXTURE_MODE') === '1';
        $baseUrl = getenv('GRIDICS_API_BASE_URL') ?: $manifest['api']['default_base_url']; $apiKey = getenv('GRIDICS_API_KEY') ?: '';
        if (!$dry && $apiKey === '') return [2, ['status'=>'error','error'=>'GRIDICS_API_KEY is required; see README.md#get-an-api-key']];
        $variables = []; foreach ($manifest['defaults'] as $name=>$value) $variables[$name] = getenv($name) ?: (string)$value;
        $mapping = ['market_id'=>'GRIDICS_MARKET_ID','place_id'=>'GRIDICS_PLACE_ID','parcel_id'=>'GRIDICS_PARCEL_ID','apn'=>'GRIDICS_APN','address'=>'GRIDICS_ADDRESS','postal_code'=>'GRIDICS_POSTAL_CODE'];
        foreach ($overrides as $name=>$value) if (isset($mapping[$name]) && $value !== null) $variables[$mapping[$name]] = (string)$value;
        $results=[]; $failed=false; $bytes=random_bytes(16);$bytes[6]=chr((ord($bytes[6])&15)|64);$bytes[8]=chr((ord($bytes[8])&63)|128);$hex=bin2hex($bytes);$session=substr($hex,0,8).'-'.substr($hex,8,4).'-'.substr($hex,12,4).'-'.substr($hex,16,4).'-'.substr($hex,20);
        foreach ($recipe['steps'] as $raw) {
            $step=self::substitute($raw,$variables);
            if($recipeId==='18'){$step=self::locationStep($step,$results,$variables,$session);if($step===null)continue;}
            if($recipeId==='17'){try{$step=self::appraiserStep($step,$results,$variables);}catch(RuntimeException $error){$results[]=['name'=>$step['name'],'status'=>'error','error'=>$error->getMessage()];$failed=true;break;}}
            if($recipeId==='11' && $step['name']==='candidates' && !$dry){
                $available=false;foreach(($results[0]['data']['data']??[]) as $field)if($field['name']==='development.max_buildable_area'&&($field['caller_available']??false)===true&&($field['selectable']??false)===true)$available=true;
                if(!$available){$results[]=['name'=>$step['name'],'status'=>'unavailable','http_status'=>null,'request_sent'=>false,'data'=>['messages'=>['capacity_fields unavailable']]];continue;}
            }
            $result=self::request($baseUrl,$apiKey,$step,$dry);if($recipeId==='18'&&$apiKey!=='')$result=json_decode(str_replace($apiKey,'[REDACTED]',json_encode($result)),true);if($recipeId==='18')$result['session_token']=$step['name']==='forward'?null:$session;
            if ($result['status']==='error') { if (($step['optional']??false)&&(($result['http_status']??null)===403)) $result['status']='unavailable'; else $failed=true; }
            $results[]=$result; if ($failed) break;
            if ($recipeId==='06' && $result['status']==='ok' && !$dry) {
                $seen=[]; $cursor=$result['data']['pagination']['next_cursor']??null; $rows=count($result['data']['data']??[]); $page=1;
                while ($cursor && !isset($seen[$cursor]) && $page<3 && $rows<100) {
                    $seen[$cursor]=true; $page++; $next=$step; $next['name']="page_$page"; $next['body']['cursor']=$cursor;
                    $nextResult=self::request($baseUrl,$apiKey,$next,false); $results[]=$nextResult;
                    if ($nextResult['status']!=='ok') {$failed=true;break;}
                    $rows+=count($nextResult['data']['data']??[]); $cursor=$nextResult['data']['pagination']['next_cursor']??null;
                }
            }
        }
        $output=['status'=>$failed?'error':'ok','recipe'=>$recipeId,'title'=>$recipe['title'],'execution'=>$dry?'dry_run':($fixture?'fixture':'live'),'api_base_url'=>$baseUrl,'request_count'=>count(array_filter($results,fn($item)=>$item['status']!=='dry_run'&&($item['request_sent']??true)!==false)),'results'=>$results];
        $workflow=self::workflow($recipeId,$results);if($workflow!==null)$output['workflow']=$workflow;
        return [$failed?1:0,$output];
    }

    private static function mcp(): int
    {
        $tools = [
            ['gridics_verify_credential','Verify the server-side Gridics API key','01',[]],
            ['gridics_list_counties','List entitled counties in a Market','02',['market_id'=>['type'=>'string']]],
            ['gridics_lookup_property','Look up one property','03',['place_id'=>['type'=>'string'],'address'=>['type'=>'string'],'postal_code'=>['type'=>'string']]],
            ['gridics_search_parcels','Run a bounded county parcel search','05',['place_id'=>['type'=>'string']]],
            ['gridics_get_zoning','Get zoning for one known parcel','04',['market_id'=>['type'=>'string'],'place_id'=>['type'=>'string'],'parcel_id'=>['type'=>'string']]],
        ];
        while (($line = fgets(STDIN)) !== false) {
            $message = json_decode($line, true); if (!is_array($message)) continue; if (($message['method']??'')==='notifications/initialized') continue; $id=$message['id']??null;
            if (($message['method']??'')==='initialize') $response=['jsonrpc'=>'2.0','id'=>$id,'result'=>['protocolVersion'=>'2025-06-18','capabilities'=>['tools'=>(object)[]],'serverInfo'=>['name'=>'gridics-api-cookbook','version'=>'1.0.0']]];
            elseif (($message['method']??'')==='tools/list') $response=['jsonrpc'=>'2.0','id'=>$id,'result'=>['tools'=>array_map(fn($tool)=>['name'=>$tool[0],'description'=>$tool[1],'inputSchema'=>['type'=>'object','properties'=>(object)$tool[3],'additionalProperties'=>false]],$tools)]];
            elseif (($message['method']??'')==='tools/call') { $tool=null; foreach($tools as $candidate) if($candidate[0]===($message['params']['name']??''))$tool=$candidate; if(!$tool)$response=['jsonrpc'=>'2.0','id'=>$id,'error'=>['code'=>-32602,'message'=>'unknown or disallowed tool']]; else { [$code,$output]=self::execute($tool[2],$message['params']['arguments']??[]); $response=['jsonrpc'=>'2.0','id'=>$id,'result'=>['content'=>[['type'=>'text','text'=>json_encode($output)]],'structuredContent'=>$output,'isError'=>$code!==0]]; } }
            else $response=['jsonrpc'=>'2.0','id'=>$id,'error'=>['code'=>-32601,'message'=>'method not found']];
            echo json_encode($response, JSON_UNESCAPED_SLASHES) . PHP_EOL; flush();
        }
        return 0;
    }

    public static function run(string $recipeId): int
    {
        if (in_array('--mcp', $_SERVER['argv'] ?? [], true)) return self::mcp();
        [$code,$output]=self::execute($recipeId); echo json_encode($output, JSON_PRETTY_PRINT|JSON_UNESCAPED_SLASHES) . PHP_EOL; return $code;
    }
}
