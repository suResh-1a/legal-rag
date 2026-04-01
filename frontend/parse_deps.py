import os
import json
import re

def get_imports(directory):
    imports = set()
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.ts', '.tsx', '.js', '.jsx')):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # simple regex for import 'pkg' or import { x } from 'pkg'
                        matches = re.findall(r"from ['\"]([^'\"]+)['\"]", content)
                        matches += re.findall(r"import ['\"]([^'\"]+)['\"]", content)
                        matches += re.findall(r"require\(['\"]([^'\"]+)['\"]\)", content)
                        for m in matches:
                            if not m.startswith('.') and not m.startswith('/'):
                                pkg = m.split('/')[0]
                                if pkg.startswith('@'):
                                    parts = m.split('/')
                                    if len(parts) > 1:
                                        pkg = parts[0] + '/' + parts[1]
                                imports.add(pkg)
                except:
                    pass
    return imports

implied_deps = get_imports('src')
implied_deps.update(['next', 'react', 'react-dom'])
implied_dev_deps = {'typescript', '@types/node', '@types/react', '@types/react-dom', 'eslint', 'eslint-config-next', 'postcss', 'tailwindcss', 'autoprefixer'}

with open('package-lock.json') as f:
    lock = json.load(f)

deps = {}
dev_deps = {}

for pkg in implied_deps:
    key = f"node_modules/{pkg}"
    if key in lock.get('packages', {}):
        deps[pkg] = lock['packages'][key]['version']
    else:
        # maybe an internal module or alias like @/components
        if not pkg.startswith('@/'):
            pass

for pkg in implied_dev_deps:
    key = f"node_modules/{pkg}"
    if key in lock.get('packages', {}):
        dev_deps[pkg] = lock['packages'][key]['version']

pkg_json = {
    "name": "frontend",
    "version": "0.1.0",
    "private": True,
    "scripts": {
        "dev": "next dev",
        "build": "next build",
        "start": "next start",
        "lint": "next lint"
    },
    "dependencies": deps,
    "devDependencies": dev_deps
}

with open('package.json', 'w') as f:
    json.dump(pkg_json, f, indent=2)

print("Generated package.json with dependencies:", list(deps.keys()))
