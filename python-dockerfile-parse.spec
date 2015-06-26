%if (0%{?fedora} >= 22 || 0%{?rhel} >= 8)
%global with_python3 1
%endif

%global owner DBuildService
%global project dockerfile-parse

%global commit abcdefg
%global shortcommit %(c=%{commit}; echo ${c:0:7})

Name:           python-dockerfile-parse
Version:        0.0.1
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


%if 0%{?with_python3}
%package -n python3-dockerfile-parse
Summary:        Python 3 library for Dockerfile manipulation
Group:          Development/Tools
License:        BSD
Requires:       python3-setuptools

%description -n python3-dockerfile-parse


%prep
%setup -qn dockerfile-parse-%{commit}
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
%dir %{python2_sitelib}/dock
%{python2_sitelib}/dock/*.*
%{python2_sitelib}/dock-%{version}-py2.*.egg-info

%if 0%{?with_python3}
%files -n python3-dockerfile-parse
%doc README.md
%{!?_licensedir:%global license %%doc}
%license LICENSE
%dir %{python3_sitelib}/dock
%{python3_sitelib}/dock/*.*
%{python3_sitelib}/dock/__pycache__/*.py*
%{python3_sitelib}/dock-%{version}-py3.*.egg-info


%changelog
* Thu Jun 18 2015 Jiri Popelka <jpopelka@redhat.com> - 0.0.1-1
- initial release
