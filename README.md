 # DIYNAFLUOR
The DIYNAFLUOR (**DIY** **N**ucleic **A**cid **FLUOR**ometer) is a $40 USD, open source, 3D printed, solder-free, portable, robust, DNA Fluorometer **YOU** can build!

Our Preprint is now available! (see https://www.biorxiv.org/content/10.1101/2024.12.16.626200v1)

![image](https://github.com/user-attachments/assets/3bd7db67-980f-4d07-9997-15d10ba4dda3)

The DIYNAFLUOR is designed to work with commercial and custom fluorescent DNA quantification kits, enabling measurements of nano-microgram levels of DNA.

![image](https://github.com/user-attachments/assets/0869c42b-0728-4fab-8037-7000797f385a)


Focusing on QCing Nanopore sequencing libraries, The DIYNAFLUOR aims to help remove barriers to genomic analysis (e.g., metagenomic sequencing) in resource limited settings.


## Build your own

### Quick Guide: 
#### How to build a DIYNAFLUOR:
1.	Buy the parts listed in the Bill of Materials (BOM). ([DIYNAFLUOR BOM.xlsx](DIYNAFLUOR%20BOM.xlsx))
2.	3D Print the provided .stl files in a matte black PLA. ([3D Printing Files.zip](3D%20Printing%20Files.zip))
3.	Assemble the DIYNAFLUOR. ([Build Instructions.pdf](Build%20Instructions.pdf))
4.	Flash the Arduino Uno and Install the GUI Software. ([DIYNAFLUOR.ino](https://github.com/traulab/DIYNAFLUOR/blob/main/arduino/DIYNAFLUOR.ino)), ([DIYNAFLUOR.exe](https://github.com/traulab/DIYNAFLUOR/releases/tag/release))
5.	Verify the performance of the device.

### Detailed Guide:
#### Sourcing Parts
We provide a BoM with links to suppliers for all parts. (see [DIYNAFLUOR BOM.xlsx](DIYNAFLUOR%20BOM.xlsx))

![image](https://github.com/user-attachments/assets/33baed13-4198-472f-931f-aa22586861d7)


#### 3D Print the custom parts
3D Print files are provided as .stl for 3D printing and .step for editing if needed. (see [3D Printing Files.zip](3D%20Printing%20Files.zip)) 

Printing can be accomplished on low-cost desktop 3D printers, such as the Creality Ender 3 or the Bambu Lab A1.

![image](https://github.com/user-attachments/assets/0b50c60d-b8ce-424c-8f74-edd8dd501a10)


#### Build your DIYNAFLUOR
To help researchers/teachers/students from all backgrounds, we have written a detailed Build Instructions manual (see [Build Instructions.pdf](Build%20Instructions.pdf)) that contains information on the DIYNAFLUOR’s operating principle, guidance for 3D printing parts, step-by-step build instructions, software installation guidance, and a verification protocol to make sure your DIYNAFLUOR is working as intended. 
Depending on your printer, this entire process can be accomplished in as little as 6-hours.*

![image](https://github.com/user-attachments/assets/028a4b65-122d-4d15-8554-e96111e530df)

*3D printing of all parts on a Bambu Lab A1 was able to be accomplished in ~4 hour, with construction and verification taking about 2 hours.


#### Install the Software
The DIYNAFLUOR is controlled by a low-cost Arduino Uno (or clone). Use the Arduino IDE to flash the custom firmware. (see [DIYNAFLUOR.ino](https://github.com/traulab/DIYNAFLUOR/blob/main/arduino/DIYNAFLUOR.ino))

![image](https://github.com/user-attachments/assets/33b1f898-5cd8-4806-b8fb-6f8ca5f6e7c8)

We have also developed a Windows 10/11 executable Graphical User Interface (GUI) that provides visualisation and recording of fluorescent measurements (as .csv files), as well as features like a 2-Point Calibration methodology for commercial DNA quantitation kits, and a Fluorometer mode that allows measurements at variable output LED excitation intensities. (see [DIYNAFLUOR.exe](https://github.com/traulab/DIYNAFLUOR/releases/tag/release))

![image](https://github.com/user-attachments/assets/f50fe4b1-fbd7-4535-8bd0-369d63a5338b)


#### Verify the performance of your DIYNAFLUOR
We have developed a simple verification assay using commercial fluorescent DNA quantification kits to assess if your DIYNAFLUOR is working as expected. (see [Build Instructions.pdf](Build%20Instructions.pdf))

<img width="650" alt="image" src="https://github.com/user-attachments/assets/904aeb77-8dbe-44eb-bcb3-1c4efc1ac50f">


#### Make Low-Cost DNA Measurements
Designed for STEM Educators - Quantify DNA concentrations between 0–10 ng/μL using the popular SYBR® Safe gel stain, for only $0.12 USD per measurement. (See [Protocol for Low-Cost DNA Quantification Assay.pdf](Protocol%20for%20Low-Cost%20DNA%20Quantification%20Assay.pdf))

#### Customize it
The default DIYNAFLUOR is designed to work with fluorophores with excitation and emission maximums of ~470ex/520em. Want to measure something else? Simply swap out the LED, and excitation and emission filters for your custom fluorophore. We would love to hear how your custom build goes!






## To learn more
More details about the DIYNAFLUOR and its performance can be found in our Preprint. (See https://www.biorxiv.org/content/10.1101/2024.12.16.626200v1).

Questions? Comments? Mistakes in the documents? 😅 Post a comment in the "Issues" section or contact lead author, Will Anderson (w.anderson1@uq.edu.au).


## Contributors
Everyone who made this project possible! (See [Contributors.txt](Contributors.txt))

## License
This project is licensed under the GNU GENERAL PUBLIC LICENSE Version 3 (See [LICENSE](https://github.com/traulab/DIYNAFLUOR/blob/main/LICENSE))


