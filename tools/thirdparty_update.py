
import glob
import os
import shutil
import util

util.cwdhack()

def copyglob(sources, destination):
    shutil.rmtree(destination, ignore_errors=True)
    print(destination)
    os.makedirs(destination, exist_ok=True)

    for source in sources:
        source_files = glob.glob(source)
        for file in source_files:
            shutil.copy(file, destination)

def run():
    copyglob(['../dec/src/*.cs'], 'project/thirdparty/dec')
    copyglob(['../dec/extra/recorder_enumerator/src/*.cs'], 'project/thirdparty/dec/recorder_enumerator')

    copyglob(['../ghi/src/*.cs'], 'project/thirdparty/ghi')

    copyglob(['../arbor/src/*.cs'], 'project/thirdparty/arbor')
    copyglob(['../arbor/generator/*.cs', '../arbor/generator/.gitignore', '../arbor/generator/*.csproj'], 'project/thirdparty/arbor/generator')

if __name__ == '__main__':
    run()
