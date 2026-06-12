const ACTIONABLE_RE =
  /\b(update|add|remove|rewrite|change|modify|edit|fix|delete|replace|insert|correct|implement|create|refactor|improve|resolve|apply)\b/i;

const ACTION_WORDS = [
  'update','add','remove','rewrite','change','modify','edit','fix',
  'delete','replace','insert','correct','implement','create','refactor',
  'improve','resolve','apply',
];

function _lev(a: string, b: string): number {
  const dp = Array.from({ length: a.length + 1 }, (_, i) =>
    Array.from({ length: b.length + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0))
  );
  for (let i = 1; i <= a.length; i++)
    for (let j = 1; j <= b.length; j++)
      dp[i][j] =
        a[i - 1] === b[j - 1]
          ? dp[i - 1][j - 1]
          : 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
  return dp[a.length][b.length];
}

export function isActionable(text: string): boolean {
  if (ACTIONABLE_RE.test(text)) return true;
  const words = text.toLowerCase().match(/\b\w{3,}\b/g) ?? [];
  return words.some(word =>
    ACTION_WORDS.some(action => {
      if (Math.abs(word.length - action.length) > 2) return false;
      return _lev(word, action) <= (action.length <= 4 ? 1 : 2);
    })
  );
}
