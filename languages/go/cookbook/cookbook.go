package cookbook

import (
	"bufio"
	"bytes"
	"crypto/rand"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

type step struct {
	MaxAttempts int               `json:"max_attempts"`
	Name        string            `json:"name"`
	Method      string            `json:"method"`
	Path        string            `json:"path"`
	Query       map[string]string `json:"query"`
	Body        any               `json:"body"`
	Optional    bool              `json:"optional"`
}
type recipe struct {
	ID    string `json:"id"`
	Title string `json:"title"`
	Steps []step `json:"steps"`
}
type manifestFile struct {
	API struct {
		DefaultBaseURL string `json:"default_base_url"`
	} `json:"api"`
	Defaults map[string]string `json:"defaults"`
	Recipes  []recipe          `json:"recipes"`
}

func root() string {
	_, file, _, _ := runtime.Caller(0)
	return filepath.Clean(filepath.Join(filepath.Dir(file), "../../.."))
}

func load() (manifestFile, error) {
	var manifest manifestFile
	data, err := os.ReadFile(filepath.Join(root(), "recipes", "manifest.json"))
	if err != nil {
		return manifest, err
	}
	err = json.Unmarshal(data, &manifest)
	return manifest, err
}

func dotenv() {
	data, err := os.ReadFile(filepath.Join(root(), ".env"))
	if err != nil {
		return
	}
	for _, raw := range strings.Split(string(data), "\n") {
		line := strings.TrimSpace(raw)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) == 2 {
			if _, ok := os.LookupEnv(strings.TrimSpace(parts[0])); !ok {
				_ = os.Setenv(strings.TrimSpace(parts[0]), strings.Trim(strings.TrimSpace(parts[1]), "\"'"))
			}
		}
	}
}

func replace(value any, vars map[string]string) any {
	switch item := value.(type) {
	case string:
		for key, val := range vars {
			item = strings.ReplaceAll(item, "${"+key+"}", val)
		}
		return item
	case []any:
		out := make([]any, len(item))
		for i, child := range item {
			out[i] = replace(child, vars)
		}
		return out
	case map[string]any:
		out := map[string]any{}
		for key, child := range item {
			if child != nil {
				out[key] = replace(child, vars)
			}
		}
		return out
	default:
		return item
	}
}

func normalizeStep(raw step, vars map[string]string) step {
	data, _ := json.Marshal(raw)
	var generic map[string]any
	_ = json.Unmarshal(data, &generic)
	generic = replace(generic, vars).(map[string]any)
	data, _ = json.Marshal(generic)
	var result step
	_ = json.Unmarshal(data, &result)
	return result
}

func message(status int, payload map[string]any) string {
	detail := "request failed"
	if values, ok := payload["messages"].([]any); ok {
		parts := []string{}
		for _, value := range values {
			parts = append(parts, fmt.Sprint(value))
		}
		detail = strings.Join(parts, "; ")
	}
	hints := map[int]string{401: "check GRIDICS_API_KEY", 403: "check plan, capability, and county entitlement", 404: "not found or hidden outside entitled scope", 409: "ambiguous locator", 422: "invalid request fields or IDs", 429: "rate, quota, or spending control reached", 502: "temporary upstream failure", 503: "temporary authorization, catalog, usage, or release failure"}
	hint := hints[status]
	if hint == "" {
		hint = "inspect the redacted request ID"
	}
	return fmt.Sprintf("HTTP %d: %s. %s", status, detail, hint)
}

func call(baseURL, apiKey string, item step, dry bool) map[string]any {
	target, _ := url.Parse(strings.TrimRight(baseURL, "/") + item.Path)
	query := target.Query()
	for key, value := range item.Query {
		query.Set(key, value)
	}
	target.RawQuery = query.Encode()
	if dry {
		result := map[string]any{"name": item.Name, "status": "dry_run", "request": map[string]any{"method": item.Method, "url": target.String(), "headers": map[string]string{"x-api-key": "[REDACTED]"}}}
		if item.Body != nil {
			result["request"].(map[string]any)["body"] = item.Body
		}
		return result
	}
	var encoded []byte
	if item.Body != nil {
		encoded, _ = json.Marshal(item.Body)
	}
	client := &http.Client{Timeout: 20 * time.Second}
	var last map[string]any
	maxAttempts := item.MaxAttempts
	if maxAttempts <= 0 {
		maxAttempts = 3
	}
	for attempt := 1; attempt <= maxAttempts; attempt++ {
		req, _ := http.NewRequest(item.Method, target.String(), bytes.NewReader(encoded))
		req.Header.Set("x-api-key", apiKey)
		req.Header.Set("Accept", "application/json")
		req.Header.Set("User-Agent", "zoning-api-cookbook/go")
		if item.Body != nil {
			req.Header.Set("Content-Type", "application/json")
		}
		response, err := client.Do(req)
		if err != nil {
			last = map[string]any{"name": item.Name, "status": "error", "http_status": nil, "error": "network error: " + err.Error()}
		} else {
			data, _ := io.ReadAll(io.LimitReader(response.Body, 4<<20))
			_ = response.Body.Close()
			payload := map[string]any{}
			if json.Unmarshal(data, &payload) != nil {
				payload = map[string]any{"status": "ERROR", "messages": []any{"non-JSON response"}}
			}
			if response.StatusCode >= 200 && response.StatusCode < 300 {
				return map[string]any{"name": item.Name, "status": "ok", "http_status": response.StatusCode, "request_id": response.Header.Get("x-request-id"), "data": payload}
			}
			last = map[string]any{"name": item.Name, "status": "error", "http_status": response.StatusCode, "error": message(response.StatusCode, payload), "data": payload}
			if response.StatusCode != 429 && response.StatusCode != 502 && response.StatusCode != 503 {
				return last
			}
		}
		if attempt < 3 {
			time.Sleep(time.Duration(250*(1<<(attempt-1))) * time.Millisecond)
		}
	}
	return last
}

func locationStep(item step, results []any, vars map[string]string, session string) *step {
	mode := vars["GRIDICS_LOCATION_MODE"]
	if mode == "forward" && item.Name != "suggest_1" {
		return nil
	}
	query := map[string]string{"q": vars["GRIDICS_LOCATION_QUERY"], "limit": vars["GRIDICS_LOCATION_LIMIT"]}
	for _, key := range []string{"country", "language", "proximity", "bbox"} {
		if value := vars["GRIDICS_LOCATION_"+strings.ToUpper(key)]; value != "" {
			query[key] = value
		}
	}
	item.MaxAttempts = 1
	if mode == "forward" {
		item.Name = "forward"
		item.Path = "/v2/locations/forward"
	} else if item.Name == "retrieve" {
		suggestions, _ := results[len(results)-1].(map[string]any)["data"].(map[string]any)["suggestions"].([]any)
		if len(suggestions) == 0 {
			return nil
		}
		item.Path = "/v2/locations/retrieve/" + url.PathEscape(suggestions[0].(map[string]any)["gridics_id"].(string))
		query = map[string]string{"session_token": session}
	} else {
		query["session_token"] = session
	}
	item.Query = query
	return &item
}
func locationReport(results []any) map[string]any {
	suggestions := []any{}
	features := []any{}
	provenance := []any{}
	failed := false
	mode := "suggest_retrieve"
	for _, raw := range results {
		item := raw.(map[string]any)
		name := item["name"].(string)
		data, _ := item["data"].(map[string]any)
		if strings.HasPrefix(name, "suggest") {
			if a, ok := data["suggestions"].([]any); ok {
				suggestions = a
			}
		}
		if name == "forward" {
			mode = "forward"
		}
		if name == "retrieve" || name == "forward" {
			if a, ok := data["features"].([]any); ok {
				features = a
			}
		}
		if item["status"] == "error" {
			failed = true
		}
		requestID := item["request_id"]
		if requestID == nil {
			requestID = data["response_id"]
		}
		provenance = append(provenance, map[string]any{"step": name, "status": item["status"], "request_id": requestID})
	}
	state := "no_match"
	if len(suggestions)+len(features) > 0 {
		state = "resolved"
	}
	if len(features) > 1 {
		state = "ambiguous"
	}
	if failed {
		state = "error"
	}
	return map[string]any{"kind": "location_search", "session_token": results[0].(map[string]any)["session_token"], "mode": mode, "suggestions": suggestions, "features": features, "state": state, "provenance": provenance}
}

func appraiserStep(item step, results []any, vars map[string]string) (step, error) {
	item.MaxAttempts = 1
	body, _ := item.Body.(map[string]any)
	if item.Name == "property" {
		locator := os.Getenv("GRIDICS_LOCATOR")
		if locator == "" {
			locator = "address"
		}
		if locator != "address" && locator != "apn" && locator != "parcel_id" {
			return item, fmt.Errorf("GRIDICS_LOCATOR must be address, apn or parcel_id")
		}
		if locator != "address" {
			delete(body, "address")
			key := "GRIDICS_PARCEL_ID"
			if locator == "apn" {
				key = "GRIDICS_APN"
			}
			body[locator] = vars[key]
		}
	} else if item.Name == "zoning" && len(results) > 0 {
		first := object(results[0])
		if first["status"] == "ok" {
			subject := object(object(first["data"])["data"])
			markets, _ := subject["market_ids"].([]any)
			if subject["id"] == nil || subject["place_id"] == nil || len(markets) != 1 {
				return item, fmt.Errorf("Lookup did not establish one canonical parcel/Place/Market; clarify before zoning")
			}
			item.Body = map[string]any{"group_id": subject["id"], "place_id": subject["place_id"], "market_id": markets[0]}
		}
	}
	return item, nil
}
func object(v any) map[string]any {
	m, _ := v.(map[string]any)
	if m == nil {
		return map[string]any{}
	}
	return m
}
func appraiserReport(results []any) map[string]any {
	data := func(i int) any {
		if i < len(results) {
			r := object(results[i])
			if r["status"] == "ok" {
				return object(r["data"])["data"]
			}
		}
		return nil
	}
	subject, zoning := data(0), data(1)
	p, z := object(subject), object(zoning)
	fields := object(p["fields"])
	choose := func(a, b any) any {
		if a != nil {
			return a
		}
		return b
	}
	address := choose(fields["parcel.address"], p["address"])
	apn := choose(fields["parcel.apn"], choose(object(p["identifiers"])["apn"], p["apn"]))
	code := choose(fields["zoning.code"], p["zoning_code"])
	unknowns := []string{"zoning description", "development capacity", "permitted uses (retrieve separately when authorized)"}
	if address == nil {
		unknowns = append(unknowns, "address")
	}
	if apn == nil {
		unknowns = append(unknowns, "APN")
	}
	if code == nil {
		unknowns = append(unknowns, "zoning designation")
	}
	if choose(fields["parcel.lot_area"], p["lot_area"]) == nil {
		unknowns = append(unknowns, "lot area")
	}
	buildings, _ := z["buildings"].([]any)
	has := func(keys []string) bool {
		for _, b := range buildings {
			e := object(object(b)["Envelope"])
			for _, k := range keys {
				if e[k] != nil {
					return true
				}
			}
		}
		return false
	}
	if !has([]string{"PrincipalMaxHeight", "TotalBuildingHeightFeet"}) {
		unknowns = append(unknowns, "height")
	}
	if !has([]string{"EffectivePFrontSetbackPrincipal", "EffectivePSideSetback", "EffectivePRearSetback"}) {
		unknowns = append(unknowns, "setbacks")
	}
	if zoning == nil {
		unknowns = append(unknowns, "zoning response")
	}
	provenance := []any{}
	ids := []string{}
	display := func(v any) string {
		if v == nil {
			return "unknown"
		}
		return strings.ReplaceAll(strings.ReplaceAll(fmt.Sprint(v), "\n", " "), "`", "")
	}
	for _, raw := range results {
		r := object(raw)
		requestID := choose(r["request_id"], object(object(r["data"])["meta"])["request_id"])
		provenance = append(provenance, map[string]any{"step": r["name"], "status": r["status"], "request_id": requestID})
		ids = append(ids, display(requestID))
	}
	boundary := "Factual Gridics data summary; not a formal appraisal, title opinion, legal advice, binding zoning determination or permit assurance."
	markdown := "# Gridics appraisal subject summary\n\n" + strings.Join([]string{"Address: " + display(address), "Parcel: " + display(p["id"]), "APN: " + display(apn), "Zoning designation: " + display(code), "Request IDs: " + strings.Join(ids, ", "), "Unknown/unavailable: " + strings.Join(unknowns, "; "), boundary}, "\n") + "\n"
	return map[string]any{"kind": "appraiser_zoning", "property": subject, "zoning": zoning, "provenance": provenance, "retrieved_at": time.Now().UTC().Format(time.RFC3339Nano), "unknowns": unknowns, "professional_boundary": boundary, "markdown": markdown}
}

func workflow(id string, results []any) any {
	payload := func(index int) any {
		if index >= len(results) {
			return nil
		}
		item, _ := results[index].(map[string]any)
		envelope, _ := item["data"].(map[string]any)
		return envelope["data"]
	}
	switch id {
	case "06":
		rows := []any{}
		for _, raw := range results {
			item, _ := raw.(map[string]any)
			envelope, _ := item["data"].(map[string]any)
			values, _ := envelope["data"].([]any)
			rows = append(rows, values...)
		}
		last, _ := results[len(results)-1].(map[string]any)
        envelope, _ := last["data"].(map[string]any)
        pagination, _ := envelope["pagination"].(map[string]any)
        cursor, _ := pagination["next_cursor"].(string)
        return map[string]any{"kind": "bounded_export", "rows": rows, "row_count": len(rows), "pages": len(results), "complete": cursor == ""}
	case "10":
		rows := []any{}
		for index, raw := range results {
			item, _ := raw.(map[string]any)
			rows = append(rows, map[string]any{"row_id": fmt.Sprintf("portfolio-%03d", index+1), "status": item["status"], "property": payload(index)})
		}
		return map[string]any{"kind": "portfolio_enrichment", "rows": rows}
	case "11":
		blocked := false
		for _, raw := range results {
			if raw.(map[string]any)["status"] == "unavailable" {
				blocked = true
			}
		}
		candidates := payload(1)
		if blocked {
			candidates = []any{}
		}
		status := "review_required"
		if blocked {
			status = "capability_blocked"
		}
		return map[string]any{"kind": "redevelopment_screen", "assessment_status": status, "candidates": candidates, "legal_conclusion": false}
	case "12":
		return map[string]any{"kind": "retail_shortlist", "candidates": payload(1), "scoring": "customer_defined", "excluded_datasets": []string{"demographics", "traffic", "competitors", "drive_times", "rent", "availability"}}
	case "18":
		return locationReport(results)
	case "17":
		return appraiserReport(results)
	case "13":
		provenance := []any{}
		for _, raw := range results {
			item := raw.(map[string]any)
			provenance = append(provenance, map[string]any{"step": item["name"], "request_id": item["request_id"]})
		}
		return map[string]any{"kind": "property_factsheet", "property": payload(0), "zoning": payload(1), "provenance": provenance, "customer_notes": nil}
	case "14":
		return map[string]any{"kind": "property_snapshot", "property": payload(0), "comparison_semantics": "observed API response; not an ordinance effective-date record"}
	case "15":
		property, zoning := payload(0), payload(1)
		pstatus, zstatus := "needs_review", "needs_review"
		if property != nil {
			pstatus = "meets"
		}
		if zoning != nil {
			zstatus = "meets"
		}
		return map[string]any{"kind": "due_diligence_screen", "overall": "needs_review", "rule_version": "example-v1", "criteria": []any{map[string]any{"name": "property_resolved", "status": pstatus}, map[string]any{"name": "zoning_available", "status": zstatus}}, "facts": map[string]any{"property": property, "zoning": zoning}, "legal_conclusion": false}
	}
	return nil
}

func Execute(id string, overrides map[string]any) (int, map[string]any) {
	dotenv()
	manifest, err := load()
	if err != nil {
		return 2, map[string]any{"status": "error", "error": err.Error()}
	}
	var selected *recipe
	for i := range manifest.Recipes {
		if manifest.Recipes[i].ID == id {
			selected = &manifest.Recipes[i]
			break
		}
	}
	if selected == nil {
		return 2, map[string]any{"status": "error", "error": "unknown recipe " + id}
	}
	dry := os.Getenv("GRIDICS_DRY_RUN") == "1"
	fixture := os.Getenv("GRIDICS_FIXTURE_MODE") == "1"
	baseURL := os.Getenv("GRIDICS_API_BASE_URL")
	if baseURL == "" {
		baseURL = manifest.API.DefaultBaseURL
	}
	apiKey := os.Getenv("GRIDICS_API_KEY")
	if !dry && apiKey == "" {
		return 2, map[string]any{"status": "error", "error": "GRIDICS_API_KEY is required; see README.md#get-an-api-key"}
	}
	vars := map[string]string{}
	for key, value := range manifest.Defaults {
		vars[key] = value
		if env := os.Getenv(key); env != "" {
			vars[key] = env
		}
	}
	mapping := map[string]string{"market_id": "GRIDICS_MARKET_ID", "place_id": "GRIDICS_PLACE_ID", "parcel_id": "GRIDICS_PARCEL_ID", "apn": "GRIDICS_APN", "address": "GRIDICS_ADDRESS", "postal_code": "GRIDICS_POSTAL_CODE"}
	for key, value := range overrides {
		if env, ok := mapping[key]; ok && value != nil {
			vars[env] = fmt.Sprint(value)
		}
	}
	sessionBytes := make([]byte, 16)
	if _, err := rand.Read(sessionBytes); err != nil {
		panic(err)
	}
	sessionBytes[6] = (sessionBytes[6] & 15) | 64
	sessionBytes[8] = (sessionBytes[8] & 63) | 128
	locationSession := fmt.Sprintf("%x-%x-%x-%x-%x", sessionBytes[:4], sessionBytes[4:6], sessionBytes[6:8], sessionBytes[8:10], sessionBytes[10:])
	results := []any{}
	failed := false
	for _, raw := range selected.Steps {
		item := normalizeStep(raw, vars)
		if id == "18" {
			next := locationStep(item, results, vars, locationSession)
			if next == nil {
				continue
			}
			item = *next
		}
		if id == "17" {
			adjusted, err := appraiserStep(item, results, vars)
			if err != nil {
				results = append(results, map[string]any{"name": item.Name, "status": "error", "error": err.Error()})
				failed = true
				break
			}
			item = adjusted
		}
        if id == "11" && item.Name == "candidates" && !dry {
            first, _ := results[0].(map[string]any)
            data, _ := first["data"].(map[string]any)
            fields, _ := data["data"].([]any)
            available := false
            for _, raw := range fields { field, _ := raw.(map[string]any); if field["name"] == "development.max_buildable_area" && field["caller_available"] == true && field["selectable"] == true { available = true } }
            if !available { results = append(results, map[string]any{"name": item.Name, "status": "unavailable", "http_status": nil, "request_sent": false, "data": map[string]any{"messages": []any{"capacity_fields unavailable"}}}); continue }
        }
		result := call(baseURL, apiKey, item, dry)
		if id == "18" {
			if apiKey != "" {
				raw, _ := json.Marshal(result)
				_ = json.Unmarshal([]byte(strings.ReplaceAll(string(raw), apiKey, "[REDACTED]")), &result)
			}
			result["session_token"] = nil
			if item.Name != "forward" {
				result["session_token"] = locationSession
			}
		}
		if result["status"] == "error" {
			if item.Optional && result["http_status"] == 403 {
				result["status"] = "unavailable"
			} else {
				failed = true
			}
		}
		results = append(results, result)
		if failed {
			break
		}
		if id == "06" && result["status"] == "ok" && !dry {
			seen := map[string]bool{}
			payload, _ := result["data"].(map[string]any)
			meta, _ := payload["pagination"].(map[string]any)
			cursor, _ := meta["next_cursor"].(string)
			rows, _ := payload["data"].([]any)
			rowCount, page := len(rows), 1
			for cursor != "" && !seen[cursor] && page < 3 && rowCount < 100 {
				seen[cursor] = true
				page++
				next := item
				next.Name = fmt.Sprintf("page_%d", page)
				body, _ := next.Body.(map[string]any)
				copyBody := map[string]any{}
				for key, value := range body {
					copyBody[key] = value
				}
				copyBody["cursor"] = cursor
				next.Body = copyBody
				nextResult := call(baseURL, apiKey, next, false)
				results = append(results, nextResult)
				if nextResult["status"] != "ok" {
					failed = true
					break
				}
				nextPayload, _ := nextResult["data"].(map[string]any)
				nextRows, _ := nextPayload["data"].([]any)
				rowCount += len(nextRows)
				nextMeta, _ := nextPayload["pagination"].(map[string]any)
				cursor, _ = nextMeta["next_cursor"].(string)
			}
		}
	}
	execution := "live"
	if fixture {
		execution = "fixture"
	}
	if dry {
		execution = "dry_run"
	}
	status := "ok"
	code := 0
	if failed {
		status = "error"
		code = 1
	}
	count := 0
	for _, raw := range results {
		if raw.(map[string]any)["status"] != "dry_run" && raw.(map[string]any)["request_sent"] != false {
			count++
		}
	}
	output := map[string]any{"status": status, "recipe": id, "title": selected.Title, "execution": execution, "api_base_url": baseURL, "request_count": count, "results": results}
	if derived := workflow(id, results); derived != nil {
		output["workflow"] = derived
	}
	return code, output
}

var tools = []struct {
	Name, Description, Recipe string
	Properties                map[string]any
}{
	{"gridics_verify_credential", "Verify the server-side Gridics API key", "01", map[string]any{}},
	{"gridics_list_counties", "List entitled counties in a Market", "02", map[string]any{"market_id": map[string]any{"type": "string"}}},
	{"gridics_lookup_property", "Look up one property", "03", map[string]any{"place_id": map[string]any{"type": "string"}, "address": map[string]any{"type": "string"}, "postal_code": map[string]any{"type": "string"}}},
	{"gridics_search_parcels", "Run a bounded county parcel search", "05", map[string]any{"place_id": map[string]any{"type": "string"}}},
	{"gridics_get_zoning", "Get zoning for one known parcel", "04", map[string]any{"market_id": map[string]any{"type": "string"}, "place_id": map[string]any{"type": "string"}, "parcel_id": map[string]any{"type": "string"}}},
}

func mcp() int {
	scanner := bufio.NewScanner(os.Stdin)
	encoder := json.NewEncoder(os.Stdout)
	for scanner.Scan() {
		var msg map[string]any
		if json.Unmarshal(scanner.Bytes(), &msg) != nil {
			continue
		}
		method, _ := msg["method"].(string)
		if method == "notifications/initialized" {
			continue
		}
		id := msg["id"]
		var response map[string]any
		switch method {
		case "initialize":
			response = map[string]any{"jsonrpc": "2.0", "id": id, "result": map[string]any{"protocolVersion": "2025-06-18", "capabilities": map[string]any{"tools": map[string]any{}}, "serverInfo": map[string]any{"name": "gridics-api-cookbook", "version": "1.0.0"}}}
		case "tools/list":
			list := []any{}
			for _, tool := range tools {
				list = append(list, map[string]any{"name": tool.Name, "description": tool.Description, "inputSchema": map[string]any{"type": "object", "properties": tool.Properties, "additionalProperties": false}})
			}
			response = map[string]any{"jsonrpc": "2.0", "id": id, "result": map[string]any{"tools": list}}
		case "tools/call":
			params, _ := msg["params"].(map[string]any)
			name, _ := params["name"].(string)
			var found *struct {
				Name, Description, Recipe string
				Properties                map[string]any
			}
			for i := range tools {
				if tools[i].Name == name {
					found = &tools[i]
				}
			}
			if found == nil {
				response = map[string]any{"jsonrpc": "2.0", "id": id, "error": map[string]any{"code": -32602, "message": "unknown or disallowed tool"}}
			} else {
				args, _ := params["arguments"].(map[string]any)
				code, output := Execute(found.Recipe, args)
				encoded, _ := json.Marshal(output)
				response = map[string]any{"jsonrpc": "2.0", "id": id, "result": map[string]any{"content": []any{map[string]any{"type": "text", "text": string(encoded)}}, "structuredContent": output, "isError": code != 0}}
			}
		default:
			response = map[string]any{"jsonrpc": "2.0", "id": id, "error": map[string]any{"code": -32601, "message": "method not found"}}
		}
		_ = encoder.Encode(response)
	}
	return 0
}

func Run(id string) int {
	for _, arg := range os.Args[1:] {
		if arg == "--mcp" {
			return mcp()
		}
	}
	code, output := Execute(id, map[string]any{})
	encoded, err := json.MarshalIndent(output, "", "  ")
	if err != nil {
		fmt.Fprintln(os.Stderr, errors.Unwrap(err))
		return 2
	}
	fmt.Println(string(encoded))
	return code
}
