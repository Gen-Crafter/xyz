#!/usr/bin/env python3
"""
MCP Demo Client — demonstrates how a producer AI agent discovers and invokes
compliance scanning tools via the Model Context Protocol.

Usage:
    python mcp_demo_client.py [--base-url http://localhost:8000]

This script:
  1. Connects to the AI Governance Proxy MCP server via SSE
  2. Discovers available compliance tools (list_tools)
  3. Invokes 'check_text' for a quick PII scan
  4. Invokes 'scan_agent_request' with a full agent pipeline
  5. Invokes 'get_compliance_status' for aggregate stats
"""

import asyncio
import argparse
import json
import sys
from mcp.client.sse import sse_client
from mcp import ClientSession


async def main(base_url: str):
    mcp_url = f"{base_url}/mcp/sse"
    print(f"\n{'='*70}")
    print(f"  MCP Demo Client — AI Governance Proxy")
    print(f"  Connecting to: {mcp_url}")
    print(f"{'='*70}\n")

    async with sse_client(mcp_url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            print("✅ MCP session initialized\n")

            # ── Step 1: Tool Discovery ─────────────────────────────────
            print("─" * 50)
            print("STEP 1: Tool Discovery (list_tools)")
            print("─" * 50)
            tools = await session.list_tools()
            print(f"Discovered {len(tools.tools)} tools:\n")
            for t in tools.tools:
                print(f"  🔧 {t.name}")
                print(f"     {t.description[:100]}...")
                print()

            # ── Step 2: Quick Text Check ───────────────────────────────
            print("─" * 50)
            print("STEP 2: Quick PII Scan (check_text)")
            print("─" * 50)
            test_text = (
                "Customer John Doe, SSN 123-45-6789, paid with card 4532-1234-5678-9012. "
                "His email is john.doe@example.com and API key is sk-proj-abc123def456."
            )
            print(f"Input: \"{test_text[:80]}...\"\n")

            result = await session.call_tool("check_text", {"text": test_text})
            parsed = json.loads(result.content[0].text)
            print(f"  Entities found: {parsed['entity_count']}")
            print(f"  Classifications: {', '.join(parsed['classifications'])}")
            print(f"  Regulations: {', '.join(parsed['regulations_applicable'])}")
            print(f"  Has sensitive data: {parsed['has_sensitive_data']}")
            print()

            # ── Step 3: Full Agent Pipeline Scan ───────────────────────
            print("─" * 50)
            print("STEP 3: Full Agent Scan (scan_agent_request)")
            print("─" * 50)
            scan_payload = {
                "request_id": "MCP-DEMO-001",
                "title": "MCP Demo — Healthcare Data Query",
                "source_app": "mcp-demo-agent",
                "user_input": "Find patient records for diabetes treatment outcomes",
                "tool_chain": [
                    {
                        "tool_name": "patient_db_search",
                        "description": "Search patient database",
                        "sequence": 1,
                        "input": {"query": "diabetes treatment outcomes"},
                        "output": {
                            "summary": "Patient Jane Smith (MRN: MRN-2024-78901), "
                                       "SSN 987-65-4321, diagnosed with Type 2 Diabetes. "
                                       "Treatment: Metformin 500mg. Last A1C: 7.2%",
                            "record_count": 45
                        },
                        "reasoning": "Querying patient records for diabetes treatment data",
                        "duration_ms": 120,
                        "status": "SUCCESS"
                    },
                    {
                        "tool_name": "llm_assistant_output",
                        "description": "Generate summary for user",
                        "sequence": 2,
                        "input": {"prompt": "Summarize diabetes treatment outcomes"},
                        "output": {
                            "summary": "Based on 45 patient records, the average A1C improvement was 1.3%. "
                                       "Contact billing at billing@hospital.com or call 555-123-4567 for "
                                       "insurance queries. API access key: HOSPI-KEY-abc123xyz."
                        },
                        "reasoning": "Generating patient outcome summary",
                        "duration_ms": 200,
                        "status": "SUCCESS"
                    }
                ],
                "final_output": {
                    "summary": "Diabetes treatment analysis complete with 45 patient records reviewed."
                }
            }
            print(f"  Request: {scan_payload['title']}")
            print(f"  Tools: {len(scan_payload['tool_chain'])} in chain\n")

            result = await session.call_tool("scan_agent_request", scan_payload)
            scan = json.loads(result.content[0].text)
            print(f"  Compliance Status: {scan['compliance_status']}")
            print(f"  Risk Score: {scan['risk_score']}/100")
            print(f"  Violations: {len(scan['violations'])}")
            print(f"  Regulations: {', '.join(scan.get('regulations_applicable', []))}")
            print(f"  Action: {scan['recommended_action']}")
            if scan['violations']:
                print(f"\n  Top violations:")
                for v in scan['violations'][:3]:
                    print(f"    ⚠ [{v['severity']}] {v['regulation']} — {v['description'][:80]}")
                    if v.get('remediation'):
                        print(f"      💡 {v['remediation'][:80]}")
            print()

            # ── Step 4: List Policies ──────────────────────────────────
            print("─" * 50)
            print("STEP 4: Active Policies (list_policies)")
            print("─" * 50)
            result = await session.call_tool("list_policies", {})
            policies = json.loads(result.content[0].text)
            print(f"  {policies['count']} active policies:\n")
            for p in policies['policies'][:5]:
                status = "🟢" if p['enabled'] else "🔴"
                print(f"    {status} {p['name']} [{p['regulation']}] → {p['action']}")
            print()

            # ── Step 5: Compliance Stats ───────────────────────────────
            print("─" * 50)
            print("STEP 5: Compliance Status (get_compliance_status)")
            print("─" * 50)
            result = await session.call_tool("get_compliance_status", {})
            stats = json.loads(result.content[0].text)
            print(f"  Total Scans: {stats.get('total_scans', 0)}")
            print(f"  Violations: {stats.get('violations', 0)}")
            print(f"  Clean: {stats.get('clean', 0)}")
            print(f"  Avg Risk: {stats.get('avg_risk_score', 0)}")
            print(f"  Compliance: {stats.get('compliance_percentage', 100)}%")

            print(f"\n{'='*70}")
            print("  ✅ MCP Demo Complete — All tools discovered and invoked successfully")
            print(f"{'='*70}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP Demo Client for AI Governance Proxy")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    args = parser.parse_args()
    asyncio.run(main(args.base_url))
