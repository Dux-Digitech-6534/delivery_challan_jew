# Server Deployment Notes

## Development server

SSH:

ssh frappe@187.127.132.58

User:

frappe

Bench path:

~/frappe-bench

Site:

erp.jewonline.in

## Existing bench apps observed

The bench already contains many apps including:

- erpnext
- frappe
- india_compliance
- hrms
- material_indent
- dux_voucher
- vehicle_inhouse
- purchase_register
- gh_raisoni_reports
- others

Do not modify existing apps unless specifically asked.

## New app

App name:

delivery_challan_custom

Recommended creation:

cd ~/frappe-bench
bench new-app delivery_challan_custom
bench --site erp.jewonline.in install-app delivery_challan_custom

## Local to server workflow

The user may keep files locally on Desktop and use Codex locally.

After local edits, copy files to server using scp or Git.

Possible scp example:

scp -r ./delivery_challan_custom frappe@187.127.132.58:/home/frappe/frappe-bench/apps/

However, be careful not to overwrite server-generated files accidentally.

Preferred workflow:

1. Generate app and DocTypes on server.
2. Pull/copy generated app folder locally.
3. Let Codex edit generated files.
4. Copy changed files back to server.
5. Run bench migrate and bench build if required.
6. Test.
7. Commit and push to GitHub.

## Commands after file copy

Run on server:

cd ~/frappe-bench
bench --site erp.jewonline.in migrate
bench --site erp.jewonline.in clear-cache
bench restart

If JS changes do not appear:

bench build --app delivery_challan_custom
bench --site erp.jewonline.in clear-cache
bench restart

## Testing URL

Use site:

https://erp.jewonline.in

## Git workflow

After successful testing:

cd ~/frappe-bench/apps/delivery_challan_custom
git status
git add .
git commit -m "Implement material delivery challan phase 1"
git remote add origin <github-repo-url>
git push -u origin main

If remote already exists, do not add again.

## Production deployment later

Production should install/update from GitHub only after dev server testing is successful.

Do not push to production directly from Codex without testing on erp.jewonline.in.