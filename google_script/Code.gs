// Copy and paste this into the Google Script Project into Code.gs
function triggerWorkflow() {
  const props = PropertiesService.getScriptProperties();
  const token = props.getProperty('GH_TOKEN');
  const repo = props.getProperty('GH_REPO');                          // e.g. "yourname/yourrepo"
  const workflow = props.getProperty('GH_WORKFLOW') || 'python-app.yml';
  const ref = props.getProperty('GH_REF') || 'main';

  if (!token || !repo) {
    throw new Error('Set GH_TOKEN and GH_REPO in Project Settings > Script Properties.');
  }

  const res = UrlFetchApp.fetch(
    'https://api.github.com/repos/' + repo + '/actions/workflows/' + workflow + '/dispatches',
    {
      method: 'post',
      contentType: 'application/json',
      headers: {
        Authorization: 'Bearer ' + token,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
      },
      payload: JSON.stringify({ ref: ref }),
      muteHttpExceptions: true
    }
  );

  const code = res.getResponseCode();
  Logger.log(code);
  if (code !== 204) {
    throw new Error('GitHub dispatch failed: ' + code + ' ' + res.getContentText());
  }
}