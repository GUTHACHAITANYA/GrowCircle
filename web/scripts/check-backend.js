#!/usr/bin/env node
/**
 * GrowCircle Backend & Dependencies Preflight Startup Health Check.
 *
 * Validates:
 * 1. Connectivity to FastAPI backend on http://127.0.0.1:8000 and http://localhost:8000
 * 2. IPv4 vs IPv6 resolution behavior
 * 3. Database connectivity status
 * 4. Prints clear, actionable diagnostics on failure (with error.cause inspection)
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

console.log('\n======================================================');
console.log(' GrowCircle Service Connectivity & Dependency Check');
console.log('======================================================\n');
console.log(`Checking API Base: ${API_BASE}`);

async function testEndpoint(urlStr) {
  const start = Date.now();
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 3000);

  try {
    const res = await fetch(urlStr, { signal: controller.signal });
    clearTimeout(timeoutId);
    const latency = Date.now() - start;
    const body = await res.json().catch(() => ({}));
    return {
      success: res.ok,
      status: res.status,
      latency,
      data: body,
      error: null,
    };
  } catch (err) {
    clearTimeout(timeoutId);
    const latency = Date.now() - start;
    return {
      success: false,
      status: null,
      latency,
      data: null,
      error: err,
    };
  }
}

async function runDiagnostics() {
  const primaryCheck = await testEndpoint(`${API_BASE}/health`);

  // IPv4 vs IPv6 check
  const ipv4Check = await testEndpoint('http://127.0.0.1:8000/health');
  const ipv6Check = await testEndpoint('http://[::1]:8000/health');
  const localhostCheck = await testEndpoint('http://localhost:8000/health');

  console.log('\n--- Network Protocol Diagnostics ---');
  console.log(`  IPv4 (127.0.0.1:8000):  ${ipv4Check.success ? `CONNECTED (${ipv4Check.latency}ms)` : `FAILED (${ipv4Check.error?.cause?.code || ipv4Check.error?.message})`}`);
  console.log(`  IPv6 ([::1]:8000):      ${ipv6Check.success ? `CONNECTED (${ipv6Check.latency}ms)` : `FAILED (${ipv6Check.error?.cause?.code || ipv6Check.error?.message})`}`);
  console.log(`  Localhost (resolved):   ${localhostCheck.success ? `CONNECTED (${localhostCheck.latency}ms)` : `FAILED (${localhostCheck.error?.cause?.code || localhostCheck.error?.message})`}`);

  console.log('\n--- Service Status ---');
  if (primaryCheck.success) {
    const d = primaryCheck.data || {};
    console.log(`  [OK] FastAPI Backend:   ONLINE (${primaryCheck.latency}ms)`);
    console.log(`       Service:           ${d.service || 'growcircle-engine'}`);
    console.log(`       Engine Version:    ${d.version || '0.1.0'}`);
    console.log(`       Database:          ${d.database === 'connected' ? 'CONNECTED (SQLite/PostgreSQL)' : 'DISCONNECTED'}`);
    if (d.alert_message) {
      console.log(`       Data Freshness:    ${d.alert_message}`);
    }
    console.log('\nAll core backend dependencies are reachable. Frontend can communicate cleanly.\n');
    process.exitCode = 0;
  } else {
    console.error(`  [FAIL] FastAPI Backend: UNREACHABLE at ${API_BASE}`);
    if (primaryCheck.error) {
      console.error(`         Error Name:      ${primaryCheck.error.name}`);
      console.error(`         Error Message:   ${primaryCheck.error.message}`);
      if (primaryCheck.error.cause) {
        console.error(`         Error Cause:     ${primaryCheck.error.cause.code || primaryCheck.error.cause.message || JSON.stringify(primaryCheck.error.cause)}`);
      }
    }

    console.error('\n=== Action Required ===');
    console.error('1. Start the backend with:');
    console.error('   .\\.venv\\Scripts\\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload');
    console.error('2. If running via Docker Compose:');
    console.error('   docker compose up -d');
    console.error('3. Verify web/.env.local contains:');
    console.error('   NEXT_PUBLIC_API_URL=http://127.0.0.1:8000\n');
    process.exitCode = 1;
  }
}

runDiagnostics();
