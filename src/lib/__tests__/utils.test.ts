describe('Utils', () => {
  it('should pass basic test', () => {
    expect(1 + 1).toBe(2);
  });

  it('should format currency', () => {
    const formatCurrency = (amount: number) => {
      return new Intl.NumberFormat('ja-JP', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(amount);
    };

    expect(formatCurrency(1000)).toBe('$1,000');
    expect(formatCurrency(500)).toBe('$500');
  });

  it('should format percentage', () => {
    const formatPercent = (value: number) => {
      return new Intl.NumberFormat('ja-JP', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(value);
    };

    expect(formatPercent(0.05)).toBe('5.00%');
    expect(formatPercent(0.123)).toBe('12.30%');
  });
});
