"""Run explicit independent background steps, preserving logs and stopping on errors."""
from pathlib import Path
import subprocess, sys
HERE=Path(__file__).resolve().parent
steps={'build':'build_scene.py','finalize':'finalize_scene.py','validate':'validate_scene.py','render':'render_previews.py'}
for step in sys.argv[1:]:
    script=steps[step]
    log=HERE.parent/'reports'/(step+'.log')
    print('START',step,flush=True)
    with log.open('w') as stream:
        result=subprocess.run(['/Applications/Blender.app/Contents/MacOS/Blender','--background','--factory-startup','--disable-autoexec','--python-exit-code','1','--python',str(HERE/script)],stdout=stream,stderr=subprocess.STDOUT)
    if result.returncode:
        print(log.read_text()[-5000:],flush=True)
        raise SystemExit(result.returncode)
    print('DONE',step,flush=True)
