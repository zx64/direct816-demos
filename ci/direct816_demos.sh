export TERM=${TERM:="xterm-256color"}

MICROPYTHON_FLAVOUR="zx64"
MICROPYTHON_VERSION="bw-1.28.0"

function log_success {
	echo -e "$(tput setaf 2)$1$(tput sgr0)"
}

function log_inform {
	echo -e "$(tput setaf 6)$1$(tput sgr0)"
}

function log_warning {
	echo -e "$(tput setaf 1)$1$(tput sgr0)"
}

function ci_micropython_clone {
    log_inform "Using MicroPython $MICROPYTHON_FLAVOUR/$MICROPYTHON_VERSION"
    git clone https://github.com/$MICROPYTHON_FLAVOUR/micropython "$CI_BUILD_ROOT/micropython"
    git -C "$CI_BUILD_ROOT/micropython" checkout $MICROPYTHON_VERSION
}

function ci_micropython_build_mpy_cross {
    ccache --zero-stats || true
    CROSS_COMPILE="ccache " make -C "$CI_BUILD_ROOT/micropython/mpy-cross" -j2
    ccache --show-stats || true
}

function ci_apt_install_build_deps {
    sudo apt update && sudo apt install ccache zip
}

function ci_install_build_deps {
    ci_apt_install_build_deps
    python3 -m pip install pyelftools==0.33 ar==1.0.1
}

function ci_prepare_all {
    ci_micropython_clone
    ci_micropython_build_mpy_cross
}

function ci_debug {
    log_inform "Project root: $CI_PROJECT_ROOT"
    log_inform "Build root: $CI_BUILD_ROOT"
}

function ci_build {
    ccache --zero-stats || true
    CROSS_COMPILE="ccache" MPY_DIR="$CI_BUILD_ROOT/micropython" make -C "$CI_PROJECT_ROOT/natmod" || return 1
    ccache --show-stats || true

    if [ -z ${CI_RELEASE_FILENAME+x} ]; then
        CI_RELEASE_FILENAME=direct816_demos-unknown.zip
    fi

    # Make a copy of the firmware directory in the build directory, copy in native modules
    # and zip to upload as a downloadable result.
    rm -fr "$CI_BUILD_ROOT/direct816_demos"
    mkdir "$CI_BUILD_ROOT/direct816_demos" || return 1
    cp -a -t "$CI_BUILD_ROOT/direct816_demos" "$CI_PROJECT_ROOT/firmware/"* || return 1
    cp -v "$CI_PROJECT_ROOT/natmod/"*/_*.mpy "$CI_BUILD_ROOT" || return 1
    mv -v "$CI_PROJECT_ROOT/natmod/"*/_*.mpy "$CI_BUILD_ROOT/direct816_demos/apps/direct816_demos" || return 1
    cd "$CI_BUILD_ROOT" || return 1
    rm -f direct816_demos.zip
    zip -9r direct816_demos.zip direct816_demos/ || return 1
    mv direct816_demos.zip "$CI_RELEASE_FILENAME"
}

if [ -z ${CI_USE_ENV+x} ] || [ -z ${CI_PROJECT_ROOT+x} ] || [ -z ${CI_BUILD_ROOT+x} ]; then
    SCRIPT_PATH=${BASH_SOURCE-$0}
    SCRIPT_PATH=$(dirname "$SCRIPT_PATH")
    CI_PROJECT_ROOT=$(realpath "$SCRIPT_PATH/..")
    CI_BUILD_ROOT=$(pwd)
fi

ci_debug
