# Publishing from Windows PowerShell without leaking identity

1. On GitHub, signed in as the pseudonymous account, create an empty public repository `plan-a-closure` (no README,
   licence or .gitignore). In Settings > Emails turn on "Keep my email addresses private" and "Block command line
   pushes that expose my email".
2. In PowerShell, from the folder the zip was downloaded to:

```powershell
Expand-Archive .\plan-a-closure.zip -DestinationPath "$HOME\anon"
cd "$HOME\anon\plan-a-closure"
git init -b main
git config user.name  "AnonRish"                                   # this repository only, not --global
git config user.email "<ID>+AnonRish@users.noreply.github.com"     # GitHub > Settings > Emails shows the exact address
$d = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss+0000")   # UTC: no -0400 style time-zone tell
$env:GIT_AUTHOR_DATE = $d; $env:GIT_COMMITTER_DATE = $d
git add -A
git commit -m "plan-a-closure 0.5.1"
git status --short --ignored            # must print nothing: every file in the archive is committed
git log -1 --format="%an <%ae> %ad"     # must show AnonRish, the noreply address and +0000
git remote add origin https://AnonRish@github.com/AnonRish/plan-a-closure.git   # the name before @ picks the account
git push -u origin main
```

3. If a browser opens to authorise Git, sign in as the pseudonymous account (use a private window if the browser is
   signed in to another GitHub account). "Permission denied to <another account>" means Git used saved credentials for
   that account: remove the `git:https://github.com` entries in Windows Credential Manager (Windows Credentials) and push
   again.
4. On GitHub, the Actions tab shows the CI run for the push; it should finish green in a few minutes. It also checks that
   the vendored repositories arrived complete (`closure external check`).

Before pushing, search the tree for anything personal: `Select-String -Path .\* -Pattern "<your name>" -Recurse`.
The search covers `external/` too: continental-load-registry's README and index.html give a contact e-mail address, as
they do on GitHub. Older commits in other repositories keep whatever they contained even after a later edit; to remove
something from history, replace the branch with a single new commit (`git checkout --orphan`) and force-push.

For every later commit, repeat the two `$env:GIT_*_DATE` lines first. If you edit a vendored repository, run
`closure external test --record <repo>` afterwards so that `closure external check` passes.

Suggested repository description: *Compute material-balance accounting for inference-only AI verification (AI 2040
Plan A): pre-registered builder-versus-breaker trial kit.* Topics: `ai-safety`, `compute-governance`,
`verification`.
