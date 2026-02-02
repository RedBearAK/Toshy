# Toshy NixOS Integration Tests Makefile
# Convenient shortcuts for running tests

.PHONY: all basic home-manager multi-de legacy clean help interactive

# Default target
all: basic home-manager multi-de

# Individual tests
basic:
	@echo "Running basic test..."
	@./run-tests.sh basic

home-manager:
	@echo "Running home-manager test..."
	@./run-tests.sh home-manager

multi-de:
	@echo "Running multi-DE test..."
	@./run-tests.sh multi-de

legacy:
	@echo "Running legacy test..."
	@./run-tests.sh legacy

# Interactive mode for debugging
interactive-basic:
	@echo "Starting interactive basic test..."
	@./run-tests.sh -i basic

interactive-hm:
	@echo "Starting interactive home-manager test..."
	@./run-tests.sh -i home-manager

interactive-multi:
	@echo "Starting interactive multi-DE test..."
	@./run-tests.sh -i multi-de

# Clean up test results
clean:
	@echo "Cleaning up test results..."
	@rm -f result-*
	@rm -f result
	@echo "Clean complete"

# Run with nix flake check (all tests)
check:
	@echo "Running all tests via nix flake check..."
	@cd ../.. && nix flake check

# Verbose mode
verbose:
	@echo "Running all tests with verbose output..."
	@./run-tests.sh -v all

# Keep going on failures
keep-going:
	@echo "Running all tests, continuing on failures..."
	@./run-tests.sh -k all

# Help
help:
	@echo "Toshy NixOS Integration Tests"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  all              Run all tests (basic, home-manager, multi-de)"
	@echo "  basic            Run basic system test"
	@echo "  home-manager     Run home-manager integration test"
	@echo "  multi-de         Run multi-desktop-environment test"
	@echo "  legacy           Run legacy integration test"
	@echo "  check            Run via 'nix flake check' (all tests)"
	@echo ""
	@echo "Interactive (debugging):"
	@echo "  interactive-basic   Debug basic test"
	@echo "  interactive-hm      Debug home-manager test"
	@echo "  interactive-multi   Debug multi-DE test"
	@echo ""
	@echo "Options:"
	@echo "  verbose          Run with verbose output"
	@echo "  keep-going       Continue on test failures"
	@echo "  clean            Remove test result symlinks"
	@echo "  help             Show this help message"
	@echo ""
	@echo "Examples:"
	@echo "  make               # Run all tests"
	@echo "  make basic         # Run only basic test"
	@echo "  make interactive-hm  # Debug home-manager test"
	@echo "  make clean         # Clean up results"
