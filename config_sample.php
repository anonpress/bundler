<?php

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