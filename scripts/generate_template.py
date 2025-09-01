import os, json, yaml, re, shutil

TEMPLATE_FILE = "template.yaml"
FUNCTIONS_DIR = "src/functions"

base = {
    "AWSTemplateFormatVersion": "2010-09-09",
    "Transform": "AWS::Serverless-2016-10-31",
    "Description": "Auto-generated multi-Lambda stack",
    "Resources": {}
}

def create_clean_build_dir(fn_dir, fn_name):
    """Create a clean build directory with only code files"""
    build_dir = f"build/{fn_name}"
    
    # Remove existing build dir if it exists
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    
    # Create new build directory
    os.makedirs(build_dir, exist_ok=True)
    
    # Copy only .py files (exclude config.json)
    for file in os.listdir(fn_dir):
        if file.endswith('.py'):
            shutil.copy2(os.path.join(fn_dir, file), build_dir)
    
    return build_dir

def sanitize_logical_id(name):
    parts = re.split(r'[^a-zA-Z0-9]', name)
    return ''.join(word.capitalize() for word in parts if word)

def detect_runtime_from_code(files):
    for f in files:
        if f.endswith(".py"):
            return "python3.13", f, f.split(".")[0] + ".lambda_handler"
        if f.endswith(".js"):
            return "nodejs18.x", f, f.split(".")[0] + ".handler"
    return None, None, None

def load_cfg(path):
    if os.path.exists(path):
        with open(path) as fh:
            return json.load(fh)
    return {}

def main():
    tpl = dict(base)
    resources = {}

    for fn_name in sorted(os.listdir(FUNCTIONS_DIR)):
        fn_dir = os.path.join(FUNCTIONS_DIR, fn_name)
        if not os.path.isdir(fn_dir): continue

        files = os.listdir(fn_dir)
        runtime, code_file, default_handler = detect_runtime_from_code(files)
        if not code_file: 
            print(f"skip {fn_name}: no code file")
            continue

        cfg = load_cfg(os.path.join(fn_dir, "config.json"))

        clean_dir = create_clean_build_dir(fn_dir, fn_name)

        handler = cfg.get("handler", default_handler)
        runtime = cfg.get("runtime", runtime)
        memory = int(cfg.get("memory", 128))
        timeout = int(cfg.get("timeout", 10))
        env = {"Variables": cfg.get("env", {})}

        props = {
            "FunctionName": fn_name,
            "CodeUri": clean_dir,
            "Handler": handler,
            "Runtime": runtime,
            "MemorySize": memory,
            "Timeout": timeout,
            "Environment": env
        }
        layers = cfg.get("layers", [])
        if layers:
            props["Layers"] = layers
        
        logical_id = sanitize_logical_id(fn_name)

        # Use explicit role if provided; else allow SAM to create one
        role = cfg.get("role", "").strip()
        if role:
            props["Role"] = role
        else:
            # Let SAM create minimal role and attach policies
            policies = cfg.get("policies", ["AWSLambdaBasicExecutionRole"])
            props["Policies"] = policies

        resources[logical_id] = {"Type": "AWS::Serverless::Function", "Properties": props}

    tpl["Resources"] = resources

    with open(TEMPLATE_FILE, "w") as f:
        yaml.dump(tpl, f, sort_keys=False)

    print(f"Generated {TEMPLATE_FILE} with {len(resources)} function(s).")

if __name__ == "__main__":
    main()