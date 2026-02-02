#!/usr/bin/env bash
# Toshy NixOS Integration Test Runner
#
# This script runs the Toshy integration tests in NixOS VMs.
# Requires: Nix with flakes enabled

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print with color
print_header() {
    echo -e "${BLUE}===${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}!${NC} $1"
}

# Check if we're in the Toshy repository
if [ ! -f "flake.nix" ]; then
    print_error "Must be run from the Toshy repository root"
    exit 1
fi

# Check if Nix is available
if ! command -v nix &> /dev/null; then
    print_error "Nix is not installed or not in PATH"
    echo "Install Nix: https://nixos.org/download.html"
    exit 1
fi

# Check if flakes are enabled
if ! nix flake --help &> /dev/null; then
    print_error "Nix flakes are not enabled"
    echo "Enable flakes by adding to /etc/nix/nix.conf or ~/.config/nix/nix.conf:"
    echo "  experimental-features = nix-command flakes"
    exit 1
fi

# Display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS] [TEST]

Run Toshy NixOS integration tests.

TESTS:
  basic           Run basic system-level tests
  home-manager    Run home-manager integration tests
  multi-de        Run multi-desktop-environment tests
  legacy          Run legacy integration test
  all             Run all tests (default)

OPTIONS:
  -i, --interactive    Run test in interactive mode (opens test driver)
  -k, --keep-going     Continue on test failures
  -v, --verbose        Show detailed output
  -h, --help           Show this help message

EXAMPLES:
  $0                   # Run all tests
  $0 basic             # Run only basic tests
  $0 -i home-manager   # Run home-manager test interactively
  $0 -k all            # Run all tests, don't stop on failure

INTERACTIVE MODE:
  Interactive mode opens the NixOS test driver where you can:
  - Run individual test commands
  - Inspect the VM state
  - Debug failing tests
  - Use: machine.shell_interact() to get an interactive shell

EOF
}

# Parse arguments
INTERACTIVE=false
KEEP_GOING=false
VERBOSE=false
TEST="all"

while [[ $# -gt 0 ]]; do
    case $1 in
        -i|--interactive)
            INTERACTIVE=true
            shift
            ;;
        -k|--keep-going)
            KEEP_GOING=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        basic|home-manager|multi-de|legacy|all)
            TEST="$1"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Run a single test
run_test() {
    local test_name="$1"
    local check_name="toshy-${test_name}-test"

    print_header "Running ${test_name} test"

    if [ "$INTERACTIVE" = true ]; then
        print_warning "Starting interactive test driver..."
        print_warning "Use 'start_all()' to start VMs, then run test commands"
        print_warning "Use 'machine.shell_interact()' for interactive shell"

        nix build ".#checks.x86_64-linux.${check_name}.driverInteractive" \
            ${VERBOSE:+--verbose} \
            --out-link "result-${test_name}-driver"

        "./result-${test_name}-driver/bin/nixos-test-driver"
        return $?
    else
        if [ "$VERBOSE" = true ]; then
            nix build ".#checks.x86_64-linux.${check_name}" \
                --verbose \
                --out-link "result-${test_name}"
        else
            nix build ".#checks.x86_64-linux.${check_name}" \
                --out-link "result-${test_name}" 2>&1 | \
                grep -E "(building|success|error|failed)" || true
        fi

        local exit_code=$?
        if [ $exit_code -eq 0 ]; then
            print_success "${test_name} test passed"
            return 0
        else
            print_error "${test_name} test failed"
            return 1
        fi
    fi
}

# Run tests
main() {
    local failed_tests=()
    local passed_tests=()

    print_header "Toshy NixOS Integration Tests"
    echo ""

    # Determine which tests to run
    local tests=()
    case "$TEST" in
        all)
            tests=("basic" "home-manager" "multi-de" "legacy")
            ;;
        *)
            tests=("$TEST")
            ;;
    esac

    # Run each test
    for test in "${tests[@]}"; do
        if run_test "$test"; then
            passed_tests+=("$test")
        else
            failed_tests+=("$test")
            if [ "$KEEP_GOING" = false ]; then
                break
            fi
        fi
        echo ""
    done

    # Print summary
    print_header "Test Summary"
    echo ""

    if [ ${#passed_tests[@]} -gt 0 ]; then
        print_success "Passed tests (${#passed_tests[@]}):"
        for test in "${passed_tests[@]}"; do
            echo "  - $test"
        done
        echo ""
    fi

    if [ ${#failed_tests[@]} -gt 0 ]; then
        print_error "Failed tests (${#failed_tests[@]}):"
        for test in "${failed_tests[@]}"; do
            echo "  - $test"
        done
        echo ""
        print_warning "To debug a failed test, run:"
        print_warning "  $0 -i ${failed_tests[0]}"
        exit 1
    else
        print_success "All tests passed! ✨"
        exit 0
    fi
}

main
