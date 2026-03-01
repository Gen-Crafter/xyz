#!/usr/bin/env python3
"""
Test script: Send realistic ChatGPT-bound requests through the MITM proxy
containing GDPR and HIPAA-violating content.

Usage:
  # Via MITM proxy (real interception flow):
  python3 test_proxy_violations.py --proxy

  # Direct to filter API (bypass proxy, test backend only):
  python3 test_proxy_violations.py --direct

  # Both:
  python3 test_proxy_violations.py --proxy --direct

  # Custom host (default: 10.118.250.245):
  python3 test_proxy_violations.py --proxy --host 10.118.250.245
"""

import argparse
import json
import sys
import time
import uuid

try:
    import requests
except ImportError:
    print("Installing requests...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

# ─── Test payloads with GDPR / HIPAA violations ─────────────────────────────

VIOLATION_PAYLOADS = [
    # ──────────────────────────────────────────────
    # 1. GDPR Violation — EU Personal Data (PII)
    # ──────────────────────────────────────────────
    {
        "name": "GDPR — EU Citizen Personal Data",
        "regulation": "GDPR",
        "body": {
            "model": "gpt-4",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Summarize this customer record for our marketing report:\n"
                        "Name: Hans Mueller\n"
                        "Email: hans.mueller@example.de\n"
                        "Phone: +49 170 1234567\n"
                        "Address: Berliner Str. 42, 10115 Berlin, Germany\n"
                        "Date of Birth: 15/03/1985\n"
                        "German National ID: T220001293\n"
                        "IP Address: 192.168.1.105\n"
                        "Credit Card: 4532-0151-2345-6789 Exp 09/27 CVV 482\n"
                        "Annual Salary: €78,500\n"
                        "Political Affiliation: Green Party member since 2019\n"
                        "Religion: Catholic\n"
                        "He visited our oncology page 14 times last month."
                    ),
                }
            ],
        },
    },
    # ──────────────────────────────────────────────
    # 2. HIPAA Violation — Protected Health Info
    # ──────────────────────────────────────────────
    {
        "name": "HIPAA — Patient Medical Records",
        "regulation": "HIPAA",
        "body": {
            "model": "gpt-4",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Please draft a referral letter based on this patient chart:\n"
                        "Patient: Jane Smith, DOB: 04/22/1978\n"
                        "SSN: 123-45-6789\n"
                        "Medical Record Number: MRN-2024-88431\n"
                        "Insurance: Blue Cross ID BC-9981234\n"
                        "Primary Diagnosis: Major Depressive Disorder (F33.1)\n"
                        "Medications: Sertraline 100mg daily, Alprazolam 0.5mg PRN\n"
                        "Lab Results: HbA1c 7.2%, TSH 4.8 mIU/L\n"
                        "HIV Status: Positive (confirmed 2021-03-15)\n"
                        "Treating Physician: Dr. Robert Chen, NPI 1234567890\n"
                        "Next Appointment: 2026-03-10 at Cedar-Sinai Psychiatry Dept"
                    ),
                }
            ],
        },
    },
    # ──────────────────────────────────────────────
    # 3. Combined GDPR + HIPAA — Cross-border health data
    # ──────────────────────────────────────────────
    {
        "name": "GDPR + HIPAA — Cross-border Patient Data",
        "regulation": "GDPR + HIPAA",
        "body": {
            "model": "gpt-4",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Translate this patient discharge summary from German to English:\n"
                        "Patient: Maria Schmidt, Geburtsdatum: 12.06.1990\n"
                        "Passport: C01X00T47 (German)\n"
                        "EHIC Number: 80756099901234567890\n"
                        "Diagnosis: Breast cancer Stage II (ICD-10: C50.9)\n"
                        "Treatment: Mastectomy performed 2026-01-20\n"
                        "Genetic Test: BRCA1 mutation positive\n"
                        "Blood Type: O-negative\n"
                        "Emergency Contact: Peter Schmidt +49 151 9876543\n"
                        "Attending: Dr. Anna Weber, Charité Berlin\n"
                        "Transfer to: Mayo Clinic, Rochester MN, USA"
                    ),
                }
            ],
        },
    },
    # ──────────────────────────────────────────────
    # 4. GDPR — Special Category Data (Art. 9)
    # ──────────────────────────────────────────────
    {
        "name": "GDPR Art. 9 — Biometric & Ethnic Data",
        "regulation": "GDPR",
        "body": {
            "model": "gpt-4",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Analyze this employee profile for our HR system:\n"
                        "Employee: Ahmed Al-Rashid\n"
                        "Employee ID: EMP-20241587\n"
                        "Email: ahmed.rashid@company.eu\n"
                        "Ethnicity: Arab\n"
                        "Religion: Islam (Sunni)\n"
                        "Sexual Orientation: Homosexual (disclosed in confidence)\n"
                        "Trade Union: Member of Ver.di since 2022\n"
                        "Fingerprint Hash: 4a7d1ed414474e4033ac29ccb8653d9b\n"
                        "Facial Recognition Template ID: FR-2024-00892\n"
                        "Health: Type 2 Diabetes, on Metformin 500mg\n"
                        "Disability: Partial hearing loss (left ear)\n"
                        "Criminal Record: Cleared — minor traffic offense 2018"
                    ),
                }
            ],
        },
    },
    # ──────────────────────────────────────────────
    # 5. HIPAA — Substance Abuse & Psychiatric Records
    # ──────────────────────────────────────────────
    {
        "name": "HIPAA — Substance Abuse Records (42 CFR Part 2)",
        "regulation": "HIPAA",
        "body": {
            "model": "gpt-4",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Summarize this treatment program report for insurance review:\n"
                        "Patient: Michael Johnson, DOB: 11/30/1992\n"
                        "SSN: 987-65-4321\n"
                        "Facility: Sunrise Recovery Center, Phoenix AZ\n"
                        "Admission Date: 2026-01-05\n"
                        "Substance: Opioid Use Disorder (Fentanyl) — severe\n"
                        "Co-occurring: PTSD from military service (Iraq, 2015)\n"
                        "Medications: Buprenorphine/Naloxone 8mg/2mg sublingual\n"
                        "Urine Drug Screen 2026-02-01: Positive for benzodiazepines\n"
                        "Counselor Notes: Patient expressed suicidal ideation on 2/14\n"
                        "VA Benefits ID: 123-45-678V\n"
                        "Emergency Contact: Sarah Johnson (wife) 602-555-0147"
                    ),
                }
            ],
        },
    },
]


def color(text, code):
    return f"\033[{code}m{text}\033[0m"


def print_header(msg):
    print(f"\n{'='*70}")
    print(color(f"  {msg}", "1;36"))
    print(f"{'='*70}")


def print_result(name, regulation, response_data, elapsed):
    decision = response_data.get("decision", "N/A")
    justification = response_data.get("justification", "")
    policies = response_data.get("policies_triggered", [])
    context = response_data.get("context_analysis", {})
    risk = context.get("risk_score", "?") if isinstance(context, dict) else "?"

    # Color decision
    if decision == "BLOCK":
        dec_str = color("BLOCK", "1;31")
    elif decision == "REDACT":
        dec_str = color("REDACT", "1;33")
    elif decision == "AUDIT":
        dec_str = color("AUDIT", "1;35")
    else:
        dec_str = color(decision, "1;32")

    print(f"\n  ┌─ {color(name, '1;37')} [{regulation}]")
    print(f"  │  Decision:      {dec_str}")
    print(f"  │  Risk Score:    {risk}")
    print(f"  │  Justification: {justification[:120]}")
    if policies:
        print(f"  │  Policies:      {', '.join(str(p) for p in policies[:5])}")
    print(f"  │  Response Time: {elapsed:.1f}s")
    print(f"  └─")


# ─── Method 1: Send through MITM proxy to chatgpt.com ───────────────────────

def test_via_proxy(host: str, proxy_port: int = 8080):
    """
    Send HTTPS requests to chatgpt.com/backend-api/conversation
    routed through the MITM proxy. The proxy intercepts, sends to
    /api/v1/filter/process, and returns BLOCK/REDACT/ALLOW.
    """
    print_header("METHOD 1: Via MITM Proxy → chatgpt.com (real interception)")
    proxy_url = f"http://{host}:{proxy_port}"
    proxies = {"http": proxy_url, "https": proxy_url}
    target_url = "https://chatgpt.com/backend-api/conversation"

    print(f"  Proxy: {proxy_url}")
    print(f"  Target: {target_url}")
    print(f"  Sending {len(VIOLATION_PAYLOADS)} test requests...\n")

    for i, test in enumerate(VIOLATION_PAYLOADS, 1):
        print(f"  [{i}/{len(VIOLATION_PAYLOADS)}] Sending: {test['name']}...")
        try:
            start = time.time()
            resp = requests.post(
                target_url,
                json=test["body"],
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (AIGP-Test)",
                    "Authorization": "Bearer test-token-for-compliance-testing",
                },
                proxies=proxies,
                verify=False,  # MITM proxy uses its own CA
                timeout=60,
            )
            elapsed = time.time() - start

            # If the proxy blocked it, we get a 403 with our JSON
            if resp.status_code == 403:
                try:
                    data = resp.json()
                    if "blocked_by_governance_proxy" in str(data):
                        data["decision"] = "BLOCK"
                        print_result(test["name"], test["regulation"], data, elapsed)
                        continue
                except (json.JSONDecodeError, ValueError):
                    pass
                # 403 from the upstream server (Cloudflare, etc.)
                print(f"    {color('403 from upstream', '1;33')} (not our proxy) — {elapsed:.1f}s")

            elif resp.status_code == 401:
                # Upstream rejected auth — means proxy FORWARDED the request
                gov_action = resp.headers.get("X-AI-Governance-Proxy", "")
                gov_hdr = resp.headers.get("X-Governance-Action", "")
                action_str = gov_hdr if gov_hdr else "ALLOW/AUDIT (forwarded)"
                print(f"    Proxy action: {color(action_str, '1;33')} → "
                      f"upstream returned 401 (expected, fake token) — {elapsed:.1f}s")
                if gov_action:
                    print(f"    X-AI-Governance-Proxy: {gov_action}")

            else:
                gov_action = resp.headers.get("X-Governance-Action", "not set")
                print(f"    Status: {resp.status_code} | "
                      f"Governance-Action: {gov_action} — {elapsed:.1f}s")

        except requests.exceptions.ProxyError as e:
            err_msg = str(e)
            if "502" in err_msg or "Bad Gateway" in err_msg:
                print(f"    {color('502 from proxy', '1;33')} (possible internal block) — check proxy logs")
            else:
                print(f"    {color('PROXY ERROR', '1;31')}: {e}")
        except requests.exceptions.ConnectionError as e:
            print(f"    {color('CONNECTION ERROR', '1;31')}: {e}")
        except Exception as e:
            print(f"    {color('ERROR', '1;31')}: {type(e).__name__}: {e}")


# ─── Method 2: Direct to filter API (bypass proxy) ──────────────────────────

def test_via_direct_api(host: str, api_port: int = 8000):
    """
    Call /api/v1/filter/process directly — same payload the MITM proxy
    would send. This tests the backend compliance pipeline independently.
    """
    print_header("METHOD 2: Direct to Filter API (bypass proxy)")
    api_url = f"http://{host}:{api_port}/api/v1/filter/process"
    print(f"  API: {api_url}")
    print(f"  Sending {len(VIOLATION_PAYLOADS)} test requests...\n")

    for i, test in enumerate(VIOLATION_PAYLOADS, 1):
        print(f"  [{i}/{len(VIOLATION_PAYLOADS)}] Sending: {test['name']}...")

        payload = {
            "interception_id": str(uuid.uuid4()),
            "direction": "outbound",
            "source_ip": "10.0.0.100",
            "destination": "chatgpt.com",
            "endpoint": "/backend-api/conversation",
            "payload": test["body"],
        }

        try:
            start = time.time()
            resp = requests.post(api_url, json=payload, timeout=120)
            elapsed = time.time() - start

            if resp.status_code == 200:
                data = resp.json()
                print_result(test["name"], test["regulation"], data, elapsed)
            else:
                print(f"  {color('ERROR', '1;31')} HTTP {resp.status_code}: {resp.text[:300]}")

        except requests.exceptions.ConnectionError:
            print(f"  {color('CONNECTION ERROR', '1;31')}: Cannot reach {api_url}")
            print(f"  → Is the API running on {host}:{api_port}?")
            break
        except Exception as e:
            print(f"  {color('ERROR', '1;31')}: {type(e).__name__}: {e}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Test AI Governance Proxy with GDPR/HIPAA violating payloads"
    )
    parser.add_argument("--host", default="10.118.250.245",
                        help="Host where proxy/API is deployed (default: 10.118.250.245)")
    parser.add_argument("--proxy", action="store_true",
                        help="Send requests through MITM proxy (port 8080)")
    parser.add_argument("--direct", action="store_true",
                        help="Send requests directly to filter API (port 8000)")
    parser.add_argument("--proxy-port", type=int, default=8080)
    parser.add_argument("--api-port", type=int, default=8000)
    args = parser.parse_args()

    # Default to both if neither specified
    if not args.proxy and not args.direct:
        args.proxy = True
        args.direct = True

    print(color("\n╔══════════════════════════════════════════════════════════════╗", "1;36"))
    print(color("║   AI Governance Proxy — Compliance Violation Test Suite     ║", "1;36"))
    print(color("╚══════════════════════════════════════════════════════════════╝", "1;36"))
    print(f"  Host:  {args.host}")
    print(f"  Tests: {len(VIOLATION_PAYLOADS)} payloads (GDPR, HIPAA, combined)")
    print(f"  Modes: {'proxy ' if args.proxy else ''}{'direct-api' if args.direct else ''}")

    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    if args.proxy:
        test_via_proxy(args.host, args.proxy_port)

    if args.direct:
        test_via_direct_api(args.host, args.api_port)

    print_header("TEST COMPLETE")
    print("  Check the Live Monitor in the frontend at:")
    print(f"  http://{args.host}:4200/live-monitor")
    print(f"  http://{args.host}:4200/audit-log\n")


if __name__ == "__main__":
    main()
