# Google Mock Files Auto-Generator

Generate gmock files based on the Google Mock framework using libclang -- the Python keybindings for the 
C interface to the Clang compiler -- given mustache templates.

> This is intended for use as a starting building block to write your mock files, NOT as a drop-in 
replacement for generating mock files based on your interface files. Use it as a tool to shorten 
development effort and time :)

---

### Requirements

 + [python](http://www.python.org) (3.9+)
 + [libclang](http://clang.llvm.org) (16.0.0+)

See `requirements.txt` for module dependencies.

### Usage

```bash
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

### Supported Features

- Works with templated interfaces
- Supports most, if not all, operator overloads
- Generates a separate file for mock constructor & destructor implementation
- Can output files in a specified directory
- Outputs formatted files using `clang-format`
- Given file can have multiple interface class definitions and the appropriate mock files will be 
created for each defined interface class

> Note: Works with a stand-alone interface class i.e. will only mock methods mentioned in the given file
> - If the interface inherits from another interface, it will not mock methods in that interface unless 
    that interface is not defined in the same file as well

### Known Limitations

- Due to some limitations (or possible errors) of libclang, methods that **return** complex types
like `boost::optional<std::vector<std::pair<int, std::string>>>` are not read as CXX methods for some reason, 
and hence not mocked
    - You would have to manually add those methods to the generated file

### Example

Note that this example contains two class definitions in one file.

#### Input interface file
```c++
/**
 * @file sample-intf.h
 * @brief Sample interface for gmock auto-generation.
 * @date 2023-08-03
 *
 * @copyright Copyright (c) 2023
 *
 */

#ifndef SAMPLE_INTF_H_
#define SAMPLE_INTF_H_

#include <string>
#include <vector>

template <typename T>
class BASE_INTF
{
    virtual void baseFunc(T var) = 0;
};

template <typename T>
class SAMPLE_INTF : public BASE_INTF<T>
{
    /**
     * @brief Sample method 1.
     *
     * @param input
     * @return boost::optional<int>
     */
    virtual boost::optional<int> optionalReturnMethod(std::string input) const = 0;

    /**
     * @brief Getter for property.
     *
     * @return T
     */
    virtual T getMyProperty() const = 0;

    /**
     * @brief Setter for property.
     *
     * @param property
     */
    virtual void setMyProperty(T property) = 0;

    /**
     * @brief Multiple param method.
     *
     * @param num
     * @param word
     * @param flag
     * @return vector of strings
     */
    virtual std::vector<std::string> multipleParamMethod(int num, std::string word, bool flag) = 0;
};

#endif // SAMPLE_INTF_H_
```

#### Output mock files

- `sample-gmock.h`:
```c++
/**
 * @file    sample-gmock.h
 * @brief   Definition of a mock class for SAMPLE interface.
 *
 * @copyright Copyright (c) 2023
 *
 */

#ifndef SAMPLE_GMOCK_H_
#define SAMPLE_GMOCK_H_

#include "sample-intf.h"

template <typename T>
class SAMPLE_GMOCK : public SAMPLE_INTF<T>
{
public:
  SAMPLE_GMOCK();
  ~SAMPLE_GMOCK() override;

  MOCK_CONST_METHOD1_T(optionalReturnMethod,
                       boost::optional<int>(std::string input));
  MOCK_CONST_METHOD0_T(getMyProperty, T());
  MOCK_METHOD1_T(setMyProperty, void(T property));
  MOCK_METHOD3_T(multipleParamMethod,
                 std::vector<std::string>(int num, std::string word,
                                          bool flag));
};

#endif /* SAMPLE_GMOCK_H_ */

```

- `sample-gmock.cpp`:
```c++
/**
 * @file    sample-gmock.cpp
 * @brief   Implementation of a mock class for SAMPLE interface.
 *
 * @copyright Copyright (c) 2023
 *
 */

#include "sample-gmock.h"

template <typename T>
SAMPLE_GMOCK<T>::SAMPLE_GMOCK() = default;
template <typename T>
SAMPLE_GMOCK<T>::~SAMPLE_GMOCK() = default;

```

- `base-gmock.h`:
```c++
/**
 * @file    base-gmock.h
 * @brief   Definition of a mock class for BASE interface.
 *
 * @copyright Copyright (c) 2023
 *
 */

#ifndef BASE_GMOCK_H_
#define BASE_GMOCK_H_

#include "simple-intf.h"

template <typename T>
class BASE_GMOCK : public BASE_INTF<T>
{
public:
  BASE_GMOCK();
  ~BASE_GMOCK() override;

  MOCK_METHOD1_T(baseFunc, void(T var));
};

#endif /* BASE_GMOCK_H_ */

```

- `base-gmock.cpp`:
```c++
/**
 * @file    base-gmock.cpp
 * @brief   Implementation of a mock class for BASE interface.
 *
 * @copyright Copyright (c) 2023
 *
 */

#include "base-gmock.h"

template <typename T>
BASE_GMOCK<T>::BASE_GMOCK() = default;
template <typename T>
BASE_GMOCK<T>::~BASE_GMOCK() = default;

```

### License

Distributed under the [Boost Software License, Version 1.0](http://www.boost.org/LICENSE_1_0.txt).
