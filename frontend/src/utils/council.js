export function getCouncilTypeDisplay(councilType) {
  if (councilType === 'premium') return '💎 Premium';
  if (councilType === 'economic') return '💰 Economic';
  if (councilType === 'free') return '🆓 Free';
  if (councilType === 'custom') return '⚙ Custom';
  return councilType || 'Premium';
}
