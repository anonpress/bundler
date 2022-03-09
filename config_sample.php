<?php
/*
 * Copyright 2017 The Anonymous Press, Inc.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

// 3dcart API:
$secureURL = 'mystore.com';
$privateKey = '0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f';
$token = '0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f';

// Address validation:
$mailto = "error@mystore.com"; // send errors here
$usps_user = "123STORE4567";

// Warehouse FTP:
$ftp_host = 'warehouse.com';
$ftp_user = 'mystore@warehouse.com';
$ftp_pass = 'a good password';
$incoming_ftp_path = 'incoming/'; // upload after bundler
$outgoing_ftp_path = 'outgoing/'; // download before tracking

// Bundler:
$IgnoreSKUs = array('DigitalItem', '3dCartBundleItem', 'TestItem'); //Lines containing these SKUs will be removed
$BundleSKUs = array(						//Lines containing these SKUs will be bundled
	'Something' => array ( 100 => 'Somethingx100', 10 => 'Somethingx10' ),
	'IComeInABoxOf20' => array ( 20 => 'IComeInABoxOf20x20' ),	
);

// Hold Orders:
$DisregardSKUs = array('3dCartBundleItem', '3dcartBundleItem2'); //duplicated by 3dcart because of "bundle items"
