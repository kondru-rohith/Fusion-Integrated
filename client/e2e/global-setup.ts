import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { type APIRequestContext, type FullConfig, request } from "@playwright/test";

import { type Account, ACCOUNTS, type AccountKey, PASSWORD } from "./accounts";
import { AUTH_DIR, LOGIN_RETRY_MS, LOGIN_TRIES, stateFile } from "./support/session";

const HERE = fileURLToPath(new URL(".", import.meta.url));
const IAM_DIR = resolve(process.env.E2E_IAM_DIR ?? resolve(HERE, "../../../Fusion_System_Administrator"));


function grantRoles(): void {
  const python = resolve(IAM_DIR, "Backend/venv/bin/python");

  if (!existsSync(python)) {
    console.warn(
      `e2e: no IAM at ${IAM_DIR}; set E2E_IAM_DIR to prepare test roles`
    );
    return;
  }

  const cwd = resolve(IAM_DIR, "Backend/backend");

  const env = Object.fromEntries(
    Object.entries(process.env).filter(
      ([key]) => key !== "DJANGO_SETTINGS_MODULE" && !key.startsWith("DB_")
    )
  );

  try {
    // Populate the IAM role catalogue.
    execFileSync(
      python,
      ["manage.py", "seed_iam_roles"],
      { cwd, env, stdio: "inherit" }
    );

    // Synchronize ERP identities.
    execFileSync(
      python,
      ["manage.py", "sync_identity", "--keep-missing"],
      { cwd, env, stdio: "inherit" }
    );

    // Prepare the synthetic placement officer E2E account.
    const fixture = [
      "from iam.models import IamUser, IamUserDesignation, IamRole",
      "user = IamUser.objects.get(username='stf00062', is_active=True)",
      "role = IamRole.objects.get(code='placement_officer', is_active=True)",
      "assert user.kind in role.kinds, 'Placement officer role is not allowed for this account kind'",
      "IamUserDesignation.objects.update_or_create(",
      "    erp_user_id=user.erp_user_id, designation=role.code",
      ")",
      "print('E2E placement officer fixture prepared:', user.username)",
    ].join("\n");

    execFileSync(
      python,
      ["manage.py", "shell", "-c", fixture],
      { cwd, env, stdio: "inherit" }
    );

  } catch (err) {
    throw new Error(`e2e: IAM setup failed: ${String(err)}`);
  }
}


async function rolesOf(api: APIRequestContext): Promise<string[] | null> {
  const me = await api.get("/api/v1/me");
  return me.ok() ? ((await me.json()) as { roles: string[] }).roles : null;
}

// The IAM allows five logins a minute per caller, and every test signs in from here.
async function logIn(api: APIRequestContext, account: Account): Promise<void> {
  for (let attempt = 1; attempt <= LOGIN_TRIES; attempt++) {
    const res = await api.post("/api/v1/auth/login",
      { data: { username: account.username, password: PASSWORD } });
    if (res.ok()) return;
    if (attempt < LOGIN_TRIES) await new Promise((r) => setTimeout(r, LOGIN_RETRY_MS));
  }
  throw new Error(`e2e: ${account.username} cannot sign in. Is the IAM running on a clean `
    + "fusion-dev.dump restore, with this account present?");
}

async function prepare(baseURL: string, key: AccountKey): Promise<void> {
  const account: Account = ACCOUNTS[key];
  const saved = stateFile(key);
  const api = await request.newContext({
    baseURL, storageState: existsSync(saved) ? saved : undefined,
  });
  try {
    let roles = await rolesOf(api);
    const stale = roles !== null && account.grants.some((g) => !roles?.includes(g));
    if (roles === null || stale) {
      await logIn(api, account);
      roles = await rolesOf(api);
    }
    const missing = account.grants.filter((g) => !roles?.includes(g));
    if (missing.length) {
      throw new Error(`e2e: ${account.username} lacks ${missing.join(", ")}. `
        + "Set E2E_IAM_DIR so global setup can grant it, or run assign_role by hand.");
    }
    await api.storageState({ path: saved });
  } finally {
    await api.dispose();
  }
}

export default async function globalSetup(config: FullConfig): Promise<void> {
  const baseURL = config.projects[0]?.use.baseURL ?? "http://localhost:5173";
  const probe = await request.newContext({ baseURL });
  const anonymous = (await probe.get("/api/v1/me")).status();
  await probe.dispose();
  if (anonymous !== 401) {
    throw new Error(`e2e: GET /api/v1/me answered ${anonymous}, expected 401. `
      + "Start the IAM and `make dev` first.");
  }
  grantRoles();
  mkdirSync(AUTH_DIR, { recursive: true });
  for (const key of Object.keys(ACCOUNTS) as AccountKey[]) await prepare(baseURL, key);
}
