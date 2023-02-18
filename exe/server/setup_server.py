from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": ["common", "forms_gui", "logs", "test_unit", "server_files",
                 "sqlalchemy"]
}
setup(
    name="messenger_server",
    version="0.8.8",
    description="messenger_server",
    options={
        "build_exe": build_exe_options
    },
    executables=[Executable('server_.py',
                            base='Win32GUI',
                            targetName='Server.exe',
                            )]
)
