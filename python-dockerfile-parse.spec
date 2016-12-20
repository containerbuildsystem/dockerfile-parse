%if 0%{?rhel} && 0%{?rhel} <= 6
%{!?__python2: %global __python2 /usr/bin/python2}
%{!?python2_sitelib: %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python2_sitearch: %global python2_sitearch %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%{!?python2_version: %global python2_version %(%{__python2} -c "import sys; sys.stdout.write(sys.version[:3])")}
%endif

%if 0%{?rhel} && 0%{?rhel} <= 7
%{!?py2_build: %global py2_build %{__python2} setup.py build}
%{!?py2_install: %global py2_install %{__python2} setup.py install --skip-build --root %{buildroot}}
%endif

%if (0%{?fedora} >= 21 || 0%{?rhel} >= 8)
%global with_python3 1
%endif

%global with_check 1

%global owner DBuildService
%global project dockerfile-parse

%global commit 9d2da5f60f020647651fbc3030c8337ac854438d
%global shortcommit %(c=%{commit}; echo ${c:0:7})

Name:           python-dockerfile-parse
Version:        0.0.6
Release:        1%{?dist}

Summary:        Python library for Dockerfile manipulation
Group:          Development/Tools
License:        BSD
URL:            https://github.com/%{owner}/%{project}
Source0:        https://github.com/%{owner}/%{project}/archive/%{commit}/%{project}-%{commit}.tar.gz

BuildArch:      noarch

BuildRequires:  python2-devel
BuildRequires:  python-setuptools
%if 0%{?with_check}
BuildRequires:  pytest, python-six
%endif # with_check

Requires:       python-setuptools

# defined in /usr/lib/rpm/macros.d/macros.python
# if python_provide() is defined, call python_provide(python-%%{project})
# which may eventually add Provides: ... (see the function definition)
%{?python_provide:%python_provide python-%{project}}

%if 0%{?with_python3}
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
%if 0%{?with_check}
BuildRequires:  python3-pytest
%endif # with_check
%endif # with_python3


%description
Python library for Dockerfile manipulation

%if 0%{?with_python3}
%package -n python3-%{project}
Summary:        Python 3 library for Dockerfile manipulation
Group:          Development/Tools
License:        BSD
%{?python_provide:%python_provide python3-%{project}}
Requires:       python3-setuptools

%description -n python3-%{project}
Python 3 library for Dockerfile manipulation
%endif # with_python3

%prep
%setup -n %{project}-%{commit}


%build
%py2_build

%if 0%{?with_python3}
%py3_build
%endif # with_python3


%install
%py2_install

%if 0%{?with_python3}
%py3_install
%endif # with_python3


%if 0%{?with_check}
%check
LANG=en_US.utf8 py.test-%{python2_version} -vv tests

%if 0%{?with_python3}
LANG=en_US.utf8 py.test-%{python3_version} -vv tests
%endif # with_python3
%endif # with_check

%files
%doc README.md
%{!?_licensedir:%global license %doc}
%license LICENSE
%dir %{python2_sitelib}/dockerfile_parse
%{python2_sitelib}/dockerfile_parse/*.*
%{python2_sitelib}/dockerfile_parse-%{version}-py2.*.egg-info

%if 0%{?with_python3}
%files -n python3-%{project}
%doc README.md
%{!?_licensedir:%global license %doc}
%license LICENSE
%dir %{python3_sitelib}/dockerfile_parse
%dir %{python3_sitelib}/dockerfile_parse/__pycache__
%{python3_sitelib}/dockerfile_parse/*.*
%{python3_sitelib}/dockerfile_parse/__pycache__/*.py*
%{python3_sitelib}/dockerfile_parse-%{version}-py3.*.egg-info
%endif # with_python3

%changelog
* Tue Dec 20 2016 Tim Waugh <twaugh@redhat.com> - 0.0.6-1
- 0.0.6

* Fri Nov 20 2015 Jiri Popelka <jpopelka@redhat.com> - 0.0.5-3
- don't use py3dir
- new python macros
- use python_provide macro

* Fri Nov 06 2015 Jiri Popelka <jpopelka@redhat.com> - 0.0.5-2
- %%check section

* Mon Sep 21 2015 Jiri Popelka <jpopelka@redhat.com> - 0.0.5-1
- 0.0.5

* Thu Aug 27 2015 Jiri Popelka <jpopelka@redhat.com> - 0.0.4-1
- 0.0.4

* Tue Jun 30 2015 Jiri Popelka <jpopelka@redhat.com> - 0.0.3-2
- define macros for RHEL-6

* Fri Jun 26 2015 Jiri Popelka <jpopelka@redhat.com> - 0.0.3-1
- 0.0.3

* Fri Jun 26 2015 Jiri Popelka <jpopelka@redhat.com> - 0.0.2-1
- 0.0.2

* Thu Jun 18 2015 Jiri Popelka <jpopelka@redhat.com> - 0.0.1-1
- initial release
