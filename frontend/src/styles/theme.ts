export const colors = {
  primary: '#1A365D',
  accent: '#3182CE',
  success: '#38A169',
  warning: '#DD6B20',
  danger: '#E53E3E',
  bg: '#FFFFFF',
  bgSecondary: '#F7FAFC',
  border: '#E2E8F0',
  textSecondary: '#718096',
} as const;

export function scoreColor(score: number): string {
  if (score >= 0.7) return colors.success;
  if (score >= 0.4) return colors.warning;
  return colors.danger;
}

export function scoreLabel(score: number): string {
  if (score >= 0.7) return '忠实';
  if (score >= 0.4) return '部分忠实';
  return '低相关';
}
