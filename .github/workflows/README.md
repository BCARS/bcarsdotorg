# GitHub Actions Workflow for Calendar Updates

## Overview

The `update-calendar.yml` workflow automatically updates the activities page by fetching the latest events from Groups.io and committing changes to the repository.

## How It Works

1. **Runs Daily**: Executes at 6 AM UTC every day
2. **Manual Trigger**: Can also be triggered manually via GitHub's "Actions" tab
3. **Fetches Calendar**: Downloads the public iCal feed from Groups.io
4. **Generates Schedule**: Runs `generate_from_ics.py` to update `content/200-activities.md`
5. **Commits Changes**: If the file changed, commits and pushes back to main branch
6. **Skip CI**: Uses `[skip ci]` to prevent triggering other workflows

## Setup

### 1. Ensure Tools Are in Repository

The workflow needs these files to be committed:
- `tools/pyproject.toml` - Project dependencies
- `tools/generate_from_ics.py` - Calendar generator script
- `tools/groupsio_client.py` - API client (not used but may be imported)

**Note**: You don't need to commit `.venv/` or other generated files - the workflow installs dependencies fresh.

### 2. Directory Structure

```
.github/
  workflows/
    update-calendar.yml          ← Workflow file
tools/
  pyproject.toml                 ← Dependencies definition
  generate_from_ics.py           ← Calendar generator
  groupsio_client.py             ← (May be imported)
  (other tool files)             ← Optional, not used by workflow
content/
  200-activities.md              ← Target file to update
```

### 3. Permissions

The workflow uses `GITHUB_TOKEN` which is automatically provided by GitHub Actions. No additional secrets needed!

**Default permissions are sufficient** for:
- ✅ Checking out code
- ✅ Committing changes
- ✅ Pushing to main branch

If your repository has protected branches, you may need to:
1. Go to Settings → Actions → General
2. Under "Workflow permissions" ensure "Read and write permissions" is selected
3. Or add the workflow to the list of apps that can push to protected branches

## Manual Trigger

To manually run the workflow:

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Select **Update Activities Calendar** workflow
4. Click **Run workflow** button
5. Select branch (usually `main`)
6. Click **Run workflow**

## Monitoring

### View Workflow Runs

- Go to **Actions** tab in your repository
- Click on **Update Activities Calendar**
- See history of runs with status (✅ success, ❌ failed)

### Check Commits

Automated commits will appear in your commit history as:
```
chore: update activities calendar [skip ci]
Author: github-actions[bot]
```

### Notifications

GitHub will notify you via email/notifications if a workflow fails.

## Troubleshooting

### Workflow Fails to Push

**Error**: `failed to push some refs` or permission denied

**Solution**: 
1. Check Settings → Actions → General → Workflow permissions
2. Enable "Read and write permissions"

### Dependencies Installation Fails

**Error**: Can't install icalendar or other packages

**Solution**:
1. Check `tools/pyproject.toml` is committed
2. Ensure dependency versions are compatible
3. Check workflow logs for specific error

### No Changes Detected But Should Be

**Error**: Workflow runs but doesn't commit

**Check**:
1. Run `python tools/generate_from_ics.py` locally to see if it makes changes
2. Check if `content/200-activities.md` already has latest content
3. Review workflow logs for the "Check for changes" step

### Python Version Issues

**Error**: Module not found or syntax errors

**Solution**: Workflow uses Python 3.11 which supports all required features. If issues occur:
1. Check if dependencies are compatible with Python 3.11
2. Adjust `python-version` in workflow if needed

## Customization

### Change Schedule

Edit the cron expression in `update-calendar.yml`:

```yaml
schedule:
  - cron: '0 6 * * *'  # 6 AM UTC daily
```

**Examples**:
- `0 */6 * * *` - Every 6 hours
- `0 6 * * 1` - Every Monday at 6 AM
- `0 6 1 * *` - First day of month at 6 AM
- `0 6 * * 0,3` - Sunday and Wednesday at 6 AM

Use [crontab.guru](https://crontab.guru/) to help generate cron expressions.

### Change Commit Message

Edit the commit step:

```yaml
git commit -m "chore: update activities calendar [skip ci]"
```

**Note**: Keep `[skip ci]` to prevent infinite loops if you have other workflows triggered by pushes.

### Update Multiple Files

If you want to update other files too:

```yaml
- name: Commit and push if changed
  if: steps.git-check.outputs.changed == 'true'
  run: |
    git config --local user.email "github-actions[bot]@users.noreply.github.com"
    git config --local user.name "github-actions[bot]"
    git add content/200-activities.md
    git add content/other-file.md  # Add more files here
    git commit -m "chore: update activities and other content [skip ci]"
    git push
```

## Testing

### Test Locally First

Before relying on the workflow:

```bash
cd tools
python generate_from_ics.py
git diff content/200-activities.md
```

Verify the output looks correct.

### Test Workflow

1. Commit the workflow file
2. Manually trigger it via Actions tab
3. Watch the logs to ensure it completes successfully
4. Check the commit history for the automated commit

## Best Practices

1. **Monitor First Week**: Check daily that workflow runs successfully
2. **Keep Dependencies Updated**: Periodically review and update package versions
3. **Review Automated Commits**: Occasionally check automated commits look correct
4. **Manual Override**: You can always manually run `generate_from_ics.py` if needed

## Security

- ✅ No secrets required (uses public iCal feed)
- ✅ Uses official GitHub Actions
- ✅ Minimal permissions needed
- ✅ No external API keys
- ✅ All dependencies pinned in `pyproject.toml`

## Workflow File Location

The workflow file must be at:
```
.github/workflows/update-calendar.yml
```

GitHub automatically detects and runs workflows from this location.

