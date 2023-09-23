<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a name="readme-top"></a>
<!--
*** Thanks for checking out the Best-README-Template. If you have a suggestion
*** that would make this better, please fork the repo and create a pull request
*** or simply open an issue with the tag "enhancement".
*** Don't forget to give the project a star!
*** Thanks again! Now go create something AMAZING! :D
-->



<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]



<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/jakee417/Pico-Train-Switching">
    <img src="images/144.png" alt="Logo" width="144" height="144">
  </a>

<h3 align="center">Rail Yard</h3>

  <p align="center">
    MicroPython REST API for controlling a Rail Yard from a Raspberry Pi Pico W
    <br />
    <a href="https://github.com/jakee417/Pico-Train-Switching"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/jakee417/Pico-Train-Switching">View Demo</a>
    ·
    <a href="https://github.com/jakee417/Pico-Train-Switching/issues">Report Bug</a>
    ·
    <a href="https://github.com/jakee417/Pico-Train-Switching/issues">Request Feature</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project
MicroPython REST API hosted from a [`Raspberry Pi Pico W`](https://www.raspberrypi.com/documentation/microcontrollers/raspberry-pi-pico.html) capable of controlling Rail Yard devices. 

[![iOS Logo][ios-logo]](https://example.com) Rail Yard is an `iOS` app that communicates with the REST API. Download the app here: ...

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- GETTING STARTED -->
## Getting Started

There are some `macOS` prerequisites before installing the firmware and build files on your `Raspberry Pi Pico W`. Once these are completed, you can skip straight to <a href="#installation">Installation</a>.

### Prerequisites

#### Install [homebrew](https://brew.sh/#install) & [`Python`](https://www.python.org/)

Install `homebrew`:
* ```sh
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install.sh)"
  ```

Install `Python`:
* ```sh
  brew install python
  ```

Test your installation by running:
* ```sh
  which python3
  ```
You should see something like: `/usr/local/bin/python3`

#### Install [`git`](https://git-scm.com/download/mac) & download repo

Install `git`:
* ```sh
  brew install git
  ```

Clone the repo:
* ```sh
  git clone https://github.com/jakee417/Pico-Train-Switching.git
  ```

### Installation
Installing the firmware and build files:

1. Run the installation script
   ```sh
   python3 Pico-Train-Switching/install.py firmware/RPI_PICO_W-20230426-v1.20.0.uf2
   ```

> [!WARNING]  
> Ensure your `Raspberry Pi Pico W` is the only connected usb device before completing the next step.

2. Connect your `Raspberry Pi Pico W` to a usb port in [BOOTSEL mode](https://projects.raspberrypi.org/en/projects/getting-started-with-the-pico/3) 



<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- USAGE EXAMPLES -->
## Usage

* Running the REST API is automatic, simply power on your `Raspberry Pi Pico W` to interact with the REST API.

* Running the REST API in dev mode from a [MicroPython REPL](https://projects.raspberrypi.org/en/projects/getting-started-with-the-pico/4):
  ```python
  from bin.main import run; run()
  ```

_For more examples, please refer to the [Documentation](https://example.com)_

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- CONTACT -->
## Contact

Jake - [@github_handle](https://github.com/jakee417)

Project Link: [https://github.com/jakee417/Pico-Train-Switching](https://github.com/jakee417/Pico-Train-Switching)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/jakee417/Pico-Train-Switching.svg?style=for-the-badge
[contributors-url]: https://github.com/jakee417/Pico-Train-Switching/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/jakee417/Pico-Train-Switching.svg?style=for-the-badge
[forks-url]: https://github.com/jakee417/Pico-Train-Switching/network/members
[stars-shield]: https://img.shields.io/github/stars/jakee417/Pico-Train-Switching.svg?style=for-the-badge
[stars-url]: https://github.com/jakee417/Pico-Train-Switching/stargazers
[issues-shield]: https://img.shields.io/github/issues/jakee417/Pico-Train-Switching.svg?style=for-the-badge
[issues-url]: https://github.com/jakee417/Pico-Train-Switching/issues
[license-shield]: https://img.shields.io/github/license/jakee417/Pico-Train-Switching.svg?style=for-the-badge
[license-url]: https://github.com/jakee417/Pico-Train-Switching/blob/master/LICENSE.txt
[ios-logo]: images/20.png