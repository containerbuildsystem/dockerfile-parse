%bcond_without tests

%global srcname dockerfile-parse
%global modname %(n=%{srcname}; echo ${n//-/_})

Name:           python-%{srcname}
Version:        1.2.0
Release:        1%{?dist}

Summary:        Python library for Dockerfile manipulation
License:        BSD
URL:            https://github.com/containerbuildsystem/dockerfile-parse
Source0:        https://github.com/containerbuildsystem/dockerfile-parse/archive/%{version}.tar.gz

BuildArch:      noarch

%description
%{summary}.

%package -n python3-%{srcname}
Summary:        %{summary}
%{?python_provide:%python_provide python3-%{srcname}}
BuildRequires:  python3-devel
BuildRequires:  python3-setuptools
%if %{with tests}
BuildRequires:  python3-pytest
BuildRequires:  python3-six
%endif
Requires:  python3-six

%description -n python3-%{srcname}
%{summary}.

Python 3 version.

%prep
%setup -q


%build
%py3_build

%install
%py3_install

%if %{with tests}
%check
export LANG=C.UTF-8
py.test-%{python3_version} -v tests
%endif

%files -n python3-%{srcname}
%license LICENSE
%doc README.md
%{python3_sitelib}/%{modname}-*.egg-info/
%{python3_sitelib}/%{modname}/


%changelog
* Wed Jun 09 2021 Robert Cerven <rcerven@redhat.com> 1.2.0-1
- new upstream release: 1.2.0

* Fri Nov 06 2020 Robert Cerven <rcerven@redhat.com> 1.1.0-1
- new upstream release: 1.1.0

* Fri Jul 03 2020 Martin Bašti <mbasti@redhat.com> 1.0.0-1
- new upstream release: 1.0.0

* Tue Jun 02 2020 Robert Cerven <rcerven@redhat.com> 0.0.18-1
- new upstream release: 0.0.18

* Fri Apr 24 2020 Martin Bašti <mbasti@redhat.com> 0.0.17-1
- new upstream release: 0.0.17

* Tue Jan 21 2020 Robert Cerven <rcerven@redhat.com> - 0.0.16-1
- new upstream release: 0.0.16

* Mon Jul 15 2019 Robert Cerven <rcerven@redhat.com> - 0.0.15-1
- new upstream release: 0.0.15

* Fri Apr 26 2019 Robert Cerven <rcerven@redhat.com> - 0.0.14-1
- new upstream release: 0.0.14

* Wed Nov 14 2018 Robert Cerven <rcerven@redhat.com> - 0.0.13-1
- new upstream release: 0.0.13

* Fri Oct 05 2018 Robert Cerven <rcerven@redhat.com> - 0.0.12-1
- new upstream release: 0.0.12

* Wed Jun 13 2018 Robert Cerven <rcerven@redhat.com> - 0.0.11-1
- new upstream release: 0.0.11

* Fri Mar 23 2018 Robert Cerven <rcerven@redhat.com> - 0.0.10-1
- new upstream release: 0.0.10

* Mon Feb 12 2018 Robert Cerven <rcerven@redhat.com> - 0.0.9-1
- new upstream release: 0.0.9

* Tue Jan 16 2018 Robert Cerven <rcerven@redhat.com> - 0.0.8-1
- new upstream release: 0.0.8

* Mon May 22 2017 Tim Waugh <twaugh@redhat.com> - 0.0.7-1
- 0.0.7

* Fri Feb  3 2017 Tim Waugh <twaugh@redhat.com>
- Incorporate modernisations from Fedora spec file.

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
