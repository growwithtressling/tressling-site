# tressling.ai

The public website for Tressling.ai. Static HTML, hosted at HostPapa.

- `site/` is the website exactly as it is served at https://tressling.ai
- HostPapa pulls this repository every 15 minutes and copies `site/` into the tressling.ai folder
- Files are added and replaced, never deleted, by the automatic update

## How updates reach the live site

- Automatic: a cPanel cron job runs every 15 minutes, pulls `main`, and copies `site/` into `/home/danmc1/tressling.ai/`
- Manual fallback: cPanel > Git Version Control > tressling-site > Manage > Pull or Deploy > Update from Remote, then Deploy HEAD Commit (uses `.cpanel.yml`)
