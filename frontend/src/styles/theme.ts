export const colors = {
  primary: '#1E293B',
  primaryDeep: '#0F172A',
  accent: '#6366F1',
  accentHover: '#4F46E5',
  accentLight: '#818CF8',
  success: '#059669',
  warning: '#D97706',
  danger: '#DC2626',
  bg: '#FFFFFF',
  bgSecondary: '#F1F5F9',
  bgTertiary: '#F8FAFC',
  border: '#E2E8F0',
  textSecondary: '#64748B',
  textMuted: '#94A3B8',
} as const;

export function scoreColor(score: number): string {
  if (score >= 0.7) return colors.success;
  if (score >= 0.4) return colors.warning;
  return colors.danger;
}

export function scoreLabel(score: number): string {
  if (score >= 0.7) return '高相关';
  if (score >= 0.4) return '中相关';
  return '低相关';
}