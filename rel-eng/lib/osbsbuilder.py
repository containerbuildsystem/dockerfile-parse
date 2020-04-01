from tito.builder import Builder


class DockerfileParseBuilder(Builder):

    def __init__(self, **kwargs):
        super(DockerfileParseBuilder, self).__init__(**kwargs)
        # tarball has to represent Source0
        # but internal structure should remain same
        # i.e. {name}-{version} otherwise %setup -q
        # will fail
        self.tgz_filename = self.display_version + ".tar.gz"
