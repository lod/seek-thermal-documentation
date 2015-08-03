# Seek Thermal Protocol

This project documents the USB interface of the Seek Thermal camera.

This documentation is unofficial and in no way supported by Seek Thermal. Seek has stated that they will publish an SDK but no documentation has yet been released. It is hoped that the SDK will make this project obsolete.

As much of the documentation is based on trial and error no guarantee is provided. We take all care but no responsibility, following the instructions here may damage your camera or other equipment.

## Device overview

Seek Thermal (http://thermal.com/) manufactures thermal cameras for use with mobile phones.  They currently have four products, the Seek Thermal for Android, the Seek Thermal for iPhone, the Seek Thermal XR for Android and the Seek Thermal XR for iPhone. Unless otherwise specified this documentation describes interacting with the original Seek Thermal for Android.

The Seek Thermal for Android is designed to plug directly in to mobile phones supporting the USB On-The-Go protocol (OTG). As such it is a USB slave device but presents a USB Micro-B plug, a passive converter is required to plug it in to a normal USB system such as a PC.

## Further reading

Much of the information documented here was extracted from an epic eevblog forum thread.  
http://www.eevblog.com/forum/testgear/yet-another-cheap-thermal-imager-incoming/

This project's wiki summarises and indexes much of the forum's information,  
https://github.com/lod/seek-thermal-documentation/wiki
