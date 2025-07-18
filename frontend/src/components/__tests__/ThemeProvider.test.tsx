import { render, screen } from '@testing-library/react';
import { ThemeProvider } from '@/components/providers/ThemeProvider';

describe('ThemeProvider', () => {
  it('renders children with theme', () => {
    render(
      <ThemeProvider>
        <div data-testid="test-content">Test Content</div>
      </ThemeProvider>
    );

    expect(screen.getByTestId('test-content')).toBeInTheDocument();
    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('applies MUI theme correctly', () => {
    render(
      <ThemeProvider>
        <div data-testid="themed-content">Themed Content</div>
      </ThemeProvider>
    );

    const content = screen.getByTestId('themed-content');
    expect(content).toBeInTheDocument();

    // Check that MUI theme is applied by checking for CssBaseline styles
    expect(document.head.querySelector('style')).toBeTruthy();
  });
});
