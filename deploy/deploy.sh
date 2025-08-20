#!/bin/bash

# OpenShift Deployment Script for Clementine Slack Bot
# This script helps deploy the Clementine bot to OpenShift using the template

set -euo pipefail  # Exit on any error, undefined variables, and pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
TEMPLATE_FILE="openshift-template.yaml"
PARAMS_FILE="parameters.env"
NAMESPACE=""
DRY_RUN=false

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy Clementine Slack Bot to OpenShift using the template.

OPTIONS:
    -f, --template-file FILE    Template file to use (default: $TEMPLATE_FILE)
    -p, --params-file FILE      Parameters file to use (default: $PARAMS_FILE)
    -n, --namespace NAMESPACE   OpenShift namespace/project to deploy to
    -d, --dry-run              Show what would be deployed without applying
    -h, --help                 Show this help message

EXAMPLES:
    # Deploy with default settings
    $0

    # Deploy to specific namespace
    $0 --namespace my-clementine-bot

    # Dry run to see what would be deployed
    $0 --dry-run

    # Use custom parameters file
    $0 --params-file my-parameters.env
EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--template-file)
            TEMPLATE_FILE="$2"
            shift 2
            ;;
        -p|--params-file)
            PARAMS_FILE="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Check if oc command is available
if ! command -v oc &> /dev/null; then
    print_error "OpenShift CLI (oc) is not installed or not in PATH"
    exit 1
fi

# Check if logged in to OpenShift
if ! oc whoami &> /dev/null; then
    print_error "Not logged in to OpenShift. Please run 'oc login' first."
    exit 1
fi

# Check if template file exists
if [[ ! -f "$TEMPLATE_FILE" ]]; then
    print_error "Template file '$TEMPLATE_FILE' not found"
    exit 1
fi

# Check if parameters file exists
if [[ ! -f "$PARAMS_FILE" ]]; then
    print_warning "Parameters file '$PARAMS_FILE' not found"
    if [[ -f "parameters.env.example" ]]; then
        print_info "Found parameters.env.example. Please copy and customize it:"
        print_info "  cp parameters.env.example $PARAMS_FILE"
        print_info "  # Edit $PARAMS_FILE with your values"
    fi
    exit 1
fi

# Switch to namespace if specified
if [[ -n "$NAMESPACE" ]]; then
    print_info "Switching to namespace: $NAMESPACE"
    if ! oc project "$NAMESPACE" &> /dev/null; then
        print_warning "Namespace '$NAMESPACE' does not exist. Creating it..."
        oc new-project "$NAMESPACE"
    fi
fi

# Get current namespace
CURRENT_NAMESPACE=$(oc project -q)
print_info "Deploying to namespace: $CURRENT_NAMESPACE"

# Validate required parameters in the file
print_info "Validating parameters file..."
required_params=("IMAGE" "SLACK_BOT_TOKEN" "SLACK_SIGNING_SECRET" "SLACK_APP_TOKEN" "TANGERINE_API_URL" "TANGERINE_API_TOKEN")

for param in "${required_params[@]}"; do
    if ! grep -q "^${param}=" "$PARAMS_FILE"; then
        print_error "Required parameter '$param' not found in $PARAMS_FILE"
        exit 1
    fi
    
    # Check if parameter has a value (not empty after =)
    value=$(grep "^${param}=" "$PARAMS_FILE" | cut -d'=' -f2-)
    if [[ -z "$value" ]]; then
        print_error "Required parameter '$param' is empty in $PARAMS_FILE"
        exit 1
    fi
done

print_success "Parameters validation passed"

# Process template
print_info "Processing OpenShift template..."

if [[ "$DRY_RUN" == "true" ]]; then
    print_warning "DRY RUN MODE - No changes will be applied"
    oc process -f "$TEMPLATE_FILE" --param-file="$PARAMS_FILE"
else
    # Apply the template
    print_info "Applying template to OpenShift..."
    oc process -f "$TEMPLATE_FILE" --param-file="$PARAMS_FILE" | oc apply -f -
    
    print_success "Template applied successfully!"
    
    # Wait for deployment to be ready
    print_info "Waiting for deployment to be ready..."
    
    # Get app name from parameters file
    APP_NAME=$(grep "^APP_NAME=" "$PARAMS_FILE" | cut -d'=' -f2 || echo "clementine")
    
    if oc rollout status "deployment/$APP_NAME" --timeout=300s; then
        print_success "Deployment is ready!"
        
        # Show deployment info
        print_info "Deployment information:"
        oc get pods -l "app=$APP_NAME"
        
        print_info "To view logs, run:"
        print_info "  oc logs -f deployment/$APP_NAME"
        
        print_info "To check all resources, run:"
        print_info "  oc get all -l app=$APP_NAME"
        
    else
        print_error "Deployment failed to become ready within timeout"
        print_info "Check deployment status with:"
        print_info "  oc get pods -l app=$APP_NAME"
        print_info "  oc describe deployment $APP_NAME"
        print_info "  oc logs deployment/$APP_NAME"
        exit 1
    fi
fi

print_success "Deployment script completed!"
