.PHONY: install uninstall help

help:
	@echo "Available targets:"
	@echo "  make install    - Install wealthgrabber as a user-level tool (requires uv)"
	@echo "  make uninstall  - Uninstall wealthgrabber tool"
	@echo ""
	@echo "After installation, you can run 'wealthgrabber' directly without 'uv run'"
	@echo "If the command is not found, run 'uv tool update-shell' to update your PATH"

install:
	@echo "Installing wealthgrabber as a user-level tool..."
	@command -v uv >/dev/null 2>&1 || { echo "Error: uv is not installed. Please install it first: https://github.com/astral-sh/uv"; exit 1; }
	@uv tool install -e .
	@echo ""
	@echo "✓ Installation complete!"
	@echo ""
	@TOOL_DIR=$$(uv tool dir 2>/dev/null); \
	if [ -n "$$TOOL_DIR" ]; then \
		echo "Scripts installed to: $$TOOL_DIR"; \
		echo ""; \
		echo "You can now run 'wealthgrabber' directly:"; \
		echo "  wealthgrabber --help"; \
		echo ""; \
		echo "If the command is not found, ensure the tool directory is in your PATH:"; \
		echo "  export PATH=\"$$TOOL_DIR:\$$PATH\""; \
		echo ""; \
		echo "Or run 'uv tool update-shell' to automatically update your shell configuration."; \
	else \
		echo "You can now run 'wealthgrabber' directly:"; \
		echo "  wealthgrabber --help"; \
		echo ""; \
		echo "If the command is not found, run 'uv tool update-shell' to update your PATH."; \
	fi

uninstall:
	@echo "Uninstalling wealthgrabber..."
	@command -v uv >/dev/null 2>&1 || { echo "Error: uv is not installed."; exit 1; }
	@uv tool uninstall wealthgrabber || true
	@echo "✓ Uninstallation complete"
