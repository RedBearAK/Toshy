#!/usr/bin/env bash


source /etc/os-release

centos_7=false
centos_stream_8=false

# Determining CentOS version
if [[ "$VERSION_ID" == "7" ]]; then
    centos_7=true
elif [[ "$VERSION_ID" == "8" ]]; then
    centos_stream_8=true
else
    echo "Not CentOS 7 or CentOS Stream 8. Script unnecessary or incompatible."
    echo "Run the main Toshy installer script. (setup_toshy.py)"
    exit 0
fi

echo "Updating CentOS repos to use the CentOS Vault (if necessary)..."

# Define the repository directory
repo_dir="/etc/yum.repos.d"


check_and_update_repos_to_vault() {
    # Updating CentOS repos to use the CentOS Vault only if necessary
    echo "Checking and updating CentOS repository configurations..."

    # Reference commands:
    # sed -i s/mirror.centos.org/vault.centos.org/g /etc/yum.repos.d/*.repo
    # sed -i s/^#.*baseurl=http/baseurl=http/g /etc/yum.repos.d/*.repo
    # sed -i s/^mirrorlist=http/#mirrorlist=http/g /etc/yum.repos.d/*.repo

    if grep -q -e 'mirror.centos.org' -e '^#.*baseurl=http' -e '^mirrorlist=http' "${repo_dir}"/*.repo; then
        echo "Updates are necessary, modifying repository files..."

        # Update mirror.centos.org to vault.centos.org
        sudo sed -i 's/mirror.centos.org/vault.centos.org/g' "${repo_dir}"/*.repo

        # Uncomment baseurl
        sudo sed -i 's/^#.*baseurl=http/baseurl=http/g' "${repo_dir}"/*.repo

        # Comment out mirrorlist
        sudo sed -i 's/^mirrorlist=http/#mirrorlist=http/g' "${repo_dir}"/*.repo

        echo "Repository files have been updated."
    else
        echo "No updates are necessary."
    fi

    # Clearing and refreshing YUM cache
    if command -v yum &> /dev/null
    then
        echo "Refreshing YUM cache..."
        sudo yum clean all
        sudo yum makecache
        echo "YUM cache has been refreshed."
    fi
}

# Call once before trying to install SCL repos
check_and_update_repos_to_vault


# Check and install SCL repos if they are not present (for CentOS 7)
check_and_install_scl_repos() {
    local scl_repo_files=("/etc/yum.repos.d/CentOS-SCLo-scl.repo" "/etc/yum.repos.d/CentOS-SCLo-scl-rh.repo")
    local scl_repo_missing=false

    for repo_file in "${scl_repo_files[@]}"; do
        if [ ! -f "$repo_file" ]; then
            scl_repo_missing=true
            break
        fi
    done

    if [ "$scl_repo_missing" = true ]; then
        echo "SCL repositories are missing, installing..."
        sudo yum install -y centos-release-scl
        update_centos_repos_to_vault  # Call update function again if we install new repos
    else
        echo "SCL repositories are already installed."
    fi
}


if $centos_7; then

    echo "Detected CentOS 7. Checking for SCL repos, Python3 and DNF..."

    # Install the SCL repos if necessary (checks and updates repos AGAIN, if necesssary)
    check_and_install_scl_repos

    # Install python3 if not present
    if ! command -v python3 &> /dev/null; then
        echo "Installing Python3..."
        sudo yum install -y python3
    fi

    # Install dnf if not present
    if ! command -v dnf &> /dev/null; then
        echo "Installing DNF..."
        sudo yum install -y dnf
    fi

elif $centos_stream_8; then
    echo "Detected CentOS Stream 8. No other special prep necessary..."
fi

# Clearing and refreshing DNF cache
if command -v dnf &> /dev/null
then
    echo "Refreshing DNF cache..."
    sudo dnf clean all
    sudo dnf makecache
    echo "DNF cache has been refreshed."
fi

echo "Your CentOS system is fully prepped for installing Toshy."
echo "You can now run the main installer script. (setup_toshy.py)"
echo ""
