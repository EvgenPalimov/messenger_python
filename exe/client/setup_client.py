from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": ["common", "forms_gui", "logs", "test_unit", "client",
                 "databases", "sqlalchemy"]
}
setup(
    name="messenger_client",
    version="0.8.7",
    description="messenger_client",
    options={
        "build_exe": build_exe_options
    },
    executables=[Executable('client_.py',
                            base='Win32GUI',
                            targetName='Client.exe',
                            )]
)
