%if 0%{?rhel} && 0%{?rhel} <= 6
%{!?__python2: %global __python2 /usr/bin/python2}
%{!?python2_sitelib: %global python2_sitelib %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())")}
%{!?python2_sitearch: %global python2_sitearch %(%{__python2} -c "from distutils.sysconfig import get_python_lib; print(get_python_lib(1))")}
%endif

%if (0%{?fedora} >= 21 || 0%{?rhel} >= 8)
%global with_python3 1
%endif

%global owner DBuildService
%global project dockerfile-parse

%global commit 36af022e527b0ac74bd27d7c2962207c0fd41632
%global shortcommit %(c=%{commit}; echo ${c:0:7})

Name:           python-dockerfile-parse
Version:        0.0.5
Release:        1%{?dist}

Summary:        Python library for Dockerfile manipulation
Group:          Development/Tools
License:        BSD
URL:            https://github.com/%{owner}/%{project}
Source0:        https://github.com/%{owner}/%{project}/archive/%{commit}/%{project}-%{commit}.tar.gz

BuildArch:      noarch

BuildRequires:  python2-devel
BuildRequires:  python-setuptools
Requires:       python-setuptools

%if 0%{?with_python3}
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
%endif

%description
Python library for Dockerfile manipulation

%if 0%{?with_python3}
%package -n python3-%{project}
Summary:        Python 3 library for Dockerfile manipulation
Group:          Development/Tools
License:        BSD
Requires:       python3-setuptools

%description -n python3-%{project}
Python 3 library for Dockerfile manipulation
%endif # with_python3

%prep
%setup -qn %{project}-%{commit}
%if 0%{?with_python3}
rm -rf %{py3dir}
cp -a . %{py3dir}
find %{py3dir} -name '*.py' | xargs sed -i '1s|^#!python|#!%{__python3}|'
%endif # with_python3


%build
# build python package
%{__python} setup.py build
%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py build
popd
%endif # with_python3


%install
%if 0%{?with_python3}
pushd %{py3dir}
%{__python3} setup.py install --skip-build --root %{buildroot}
popd
%endif # with_python3

%{__python} setup.py install --skip-build --root %{buildroot}


%files
%doc README.md
%{!?_licensedir:%global license %%doc}
%license LICENSE
%dir %{python2_sitelib}/dockerfile_parse
%{python2_sitelib}/dockerfile_parse/*.*
%{python2_sitelib}/dockerfile_parse-%{version}-py2.*.egg-info

%if 0%{?with_python3}
%files -n python3-%{project}
%doc README.md
%{!?_licensedir:%global license %%doc}
%license LICENSE
%dir %{python3_sitelib}/dockerfile_parse
%dir %{python3_sitelib}/dockerfile_parse/__pycache__
%{python3_sitelib}/dockerfile_parse/*.*
%{python3_sitelib}/dockerfile_parse/__pycache__/*.py*
%{python3_sitelib}/dockerfile_parse-%{version}-py3.*.egg-info
%endif # with_python3

%changelog
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
