# Contributing Guide

## Submitting changes

Changes are accepted through pull requests.

Please create your feature branch from the **master** branch. Make sure to add
unit tests under the `tests` subdirectory (we use py.test and flexmock for
this). When you push new commits, tests will be triggered to be run in
[Travis CI][] and results will be shown in your pull request. You
can also run them locally from the top directory (`py.test tests`).

Follow the PEP8 coding style. This project allows 99 characters per line.

Please make sure each commit is for a complete logical change, and has a
[useful][] commit message. When making changes in response to suggestions, it is
fine to make new commits for them but please make sure to squash them into the
relevant "logical change" commit before the pull request is merged.

Before a pull request is approved it must have

- Unit tests pass
- Code coverage from testing does not decrease and new code is covered

Once it is approved by two developer team members it may be merged. To avoid
creating merge commits the pull request will be rebased during the merge.

Please read the [review checklist][] .

## Licensing

This project is licensed using the [BSD-3-Clause license][].

When submitting pull requests please make sure your commit messages include a
signed-off-by line to certify the below text:

```text
Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

You can do this by using `git commit --signoff` when committing changes, making
sure that your real name is included.

[Travis CI]: https://travis-ci.org
[useful]: http://chris.beams.io/posts/git-commit
[review checklist]: https://osbs.readthedocs.io/en/latest/contributors.html#submitting-changes
[BSD-3-Clause license]: ./LICENSE
