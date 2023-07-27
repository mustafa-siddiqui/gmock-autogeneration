# Google Mock Files Auto-generation

Generate gmock files based on the Google Mock framework using libclang -- the Python keybindings for the 
C interface to the Clang compiler -- given mustache templates.

---------

### ToDos
- [x] Constructor & Destructor missing for mock class  
- [x] Implementation file needs to be added for ctor & dtor  
- [x] Mock class & file names have to renamed according to standard  
- [x] `.conf` file not found error if not provided as argument (even though the filepath generated seems to be correct, possibly a local set up issue) => turns out it was a local set up issue...
- [x] Add requirements.txt 
- [x] Function paramters that have '`::`' in the typename like `std::string`, `std::vector`, `std::shared_ptr` 
are being replaced with `int`. This issue doesn't exist if such types are being returned by a function
- [x] Parameter names are missing from the generated mock methods
- [x] Update string (%s) formatter use to `python3` `.format()` or equivalent
    - [x] Ideal goal would be upgrade this to use `.mustache` files or something similar
- [x] Randomly omitting functions when creating mock methods??
    - [x] Removing the check for a pure virtual function fixes this
    > Note: That check ideally should be there but it doesn't return true for some functions despite them being declared pure virtual.
- [ ] Parse doesn't seem to read in a method like the following for some unknown reason:  
    `virtual std::vector<std::pair<std::string, bool>> getVectorOfPairs(std::shared_ptr<TEST_OBJECT_INTF> const &instance) = 0;`
    > Note: Not really sure of the reason why. Suspicion
    is probably due to lack of support or some error when 
    evaluating a return type like that. Nice to fix but can also just be called out at this point.
- [ ] Currently, when the `operator()` is defined, incorrect # of args will be returned. This is because 
    the function wasn't intended to handle that case but it definitely should handle those cases if the 
    script is supporting those use cases.
- [ ] Support `>>` or `>>>` directly in the function isn't robust and will break if an unusual parameter
    is given and those types are parsed.
          

### Notes

The script is now upto python3 standards, uses mustache files for templates, is very much
simplified, majorly refactored, and much new code has been introduced.

---------

### Requirements
 + [python](http://www.python.org) (3.9+)
 + [libclang](http://clang.llvm.org) (16.0.0+)

See `requirements.txt` for module dependencies.

### Download
```
git clone git@github.com:mustafa-siddiqui/gmock-autogeneration.git
```

### Usage
```sh
Usage: generateGmock.py [-h] [-d DIR] -f FILE [-e EXPR] [-l LIBCLANG]

Generate gmock files from an interface given mustache templates.

optional arguments:
  -h, --help            show this help message and exit
  -d DIR, --dir DIR     Directory to store generated mock files in. Default = current directory.
  -f FILE, --file FILE  Path to the interface file from which the mock file is to be generated.
  -e EXPR, --expr EXPR  Limit to interfaces within expression. Default = ''
  -l LIBCLANG, --libclang LIBCLANG
                        Path to libclang.so. Default = None
```

----
```
 |  
 |   Needs to be updated.  
 V  
```

### Example
```sh
./gmock.py file.hpp
```
will create mocks files in current directory for all interfaces

```sh
./gmock.py -c "gmock.conf" -d "test/mocks" -l "namespace::class" file1.hpp file2.hpp
```
will create directory 'test/mocks' and mocks files within this directory for all interfaces (contains at least one pure virtual function)
which will be within 'namespace::class' declaration

```sh
./gmock.py -d "test/mocks" file1.hpp file2.hpp -- -D PROJECT -Iproject/include
```
'--' separates arguments between script and compiler

### Integration with the build system
```sh
find project -iname "*.h" -or -iname "*.hpp" | xargs "project/externals/gmock.py"   \
    -c "project/conf/gmock.conf"                                                    \
    -d "project/test/mocks"                                                         \
    -l "Project"                                                                    \
    --                                                                              \
    -D PROJECT                                                                      \
    -Iproject/include                                                               \
```

### Features
 + it's reliable (based on clang compiler)
 + it's fast (tested on project ~200 kloc -> generation of mocs takes 3-5s on common laptop)
 + output file might be easily adopted to the project via configuration file
 + easy integration with the project build system -> generate mocks files for each interface from given files limited to the project (for example via project namespace)
 + able to generate cpp files with default constructors (to speed up compilation times)
 + generate pretty output (one mock per file)
 + mocking class templates
 + easy to extend (~300 lines of code)
 + handle c++ operators

```cpp
    virtual int operator()(int, double) = 0;
```

```cpp
    virtual int operator()(int arg0, double arg1) { return call_operator(arg0, arg1); }
    MOCK_METHOD2(call_operator, int(int, double));
```

### Configuration file
```python
#possible variables:
# file: interface file name
# dir: interface directory
# guard: header guard
# template: template parameters
# template_interface: template interface class
# interface: interface class
# mock_methods: generated gmock methods
# generated_dir: generated directory
# mock_file_hpp: mock header file
# mock_file_cpp: mock source file

mock_file_hpp = "%(interface)sMock.hpp"

file_template_hpp = """\
/*
 * file generated by gmock: %(mock_file_hpp)s
 */
#ifndef %(guard)s
#define %(guard)s

#include <gmock/gmock.h>
#include "%(dir)s/%(file)s"

%(namespaces_begin)s

%(template)sclass %(interface)sMock : public %(template_interface)s
{
public:
%(mock_methods)s
};

%(namespaces_end)s

#endif // %(guard)s

"""

mock_file_cpp = ""
file_template_cpp = ""

```

### Example of generated output
```cpp
/*
 * file generated by gmock: I2Mock.hpp
 */
#ifndef I2MOCK_HPP
#define I2MOCK_HPP

#include <gmock/gmock.h>
#include "I2.hpp"

namespace n {

class I2Mock : public I2
{
public:
    MOCK_CONST_METHOD0(f0, void());
    MOCK_METHOD1(f1, void(int));
    MOCK_METHOD1(f2, void(double));
    MOCK_METHOD2(f3, void(int, double));
    MOCK_METHOD3(f4, void(int, double, const std::string &));
    MOCK_METHOD1(f5, int(const std::string &));
    MOCK_CONST_METHOD1(f6, boost::shared_ptr<int>(const boost::shared_ptr<int> &));
    MOCK_CONST_METHOD0(f7, const int&());
    MOCK_METHOD0(f8, boost::function<void(int)>());
    MOCK_CONST_METHOD1(f9, boost::non_type<int,0>(const boost::non_type<int, 1> &));
    MOCK_METHOD0(f10, const int*const ());
    MOCK_METHOD0(f11, const void());
    virtual int operator()() { return function_call_or_cast_operator(); }
    MOCK_METHOD0(function_call_or_cast_operator, int());
};

} // namespace n

#endif // I2MOCK_HPP

```

```cpp
/*
 * file generated by gmock: TMock.hpp
 */
#ifndef TMOCK_HPP
#define TMOCK_HPP

#include <gmock/gmock.h>
#include "T.hpp"

namespace n {

template<typename Elem>
class TMock : public T<Elem>
{
public:
    MOCK_CONST_METHOD0_T(GetSize, int());
    MOCK_METHOD1_T(Push, void(const Elem &));
};

} // namespace n

#endif // TMOCK_HPP
```

### License
Distributed under the [Boost Software License, Version 1.0](http://www.boost.org/LICENSE_1_0.txt).

