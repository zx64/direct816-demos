SCRIPT_PATH=${BASH_SOURCE-$0}
SCRIPT_PATH=$(dirname "$SCRIPT_PATH")
SCRIPT_PATH=$(realpath "$SCRIPT_PATH")

function qa_prepare_all {
    pip install ruff ty
}

function qa_check {
    ruff check --config "$SCRIPT_PATH/ruff.toml" "$1"
}

function qa_fix {
    ruff check --config "$SCRIPT_PATH/ruff.toml" --fix "$1"
}

function qa_root_check {
    qa_check .
}

function qa_root_fix {
    qa_fix .
}

function qa_firmware_check {
    qa_check firmware/
}

function qa_firmware_fix {
    qa_fix firmware/
}

function qa_modules_check {
    qa_check modules/
}

function qa_modules_fix {
    qa_fix modules/
}

function qa_tools_check {
    ruff check tools/
    ty check tools/
}
