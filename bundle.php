<?php

//Sean Gillen / Anonymous Press

$debug_bundle = false; //Set to TRUE to prevent output file FTP upload and deletion -false for production

require_once('config.php');

$ftp_path = $incoming_ftp_path;

$delete_input_file = true;
$save_input_file = true; //copy to processed/

$out = date('Y-m-d HiO').'.csv'; //override


echo date('Y-m-d Hi0: '); //for logging
include('address_validation.php'); //run address validator
include('bundler.php'); //run bundler


if(!$debug_bundle){
	echo "Connecting to fulfillment server.\r\n";
	
	$ftp = ftp_connect($ftp_host);
	ftp_login($ftp,$ftp_user,$ftp_pass);
	ftp_pasv($ftp,true);
	
	if(ftp_put($ftp,$ftp_path.$out,$path.$out,FTP_ASCII)) { //If file upload successful
		echo "$out uploaded to fulfillment server.";
		
		copy($path.$out,'uploaded/'.$out);
		if($save_input_file) copy($path.$in,'processed/'.$out);
	
		include('hold_orders.php'); //change order status to Hold where necessary

		unlink($path.$out); //delete temporary output file
	}
	else var_dump(error_get_last());
	
	ftp_close($ftp);
}
else echo "Debug mode enabled. No connection made to fulfillment server.\r\n";

if($delete_input_file) unlink($path.$in); //delete input file
?>
A lack of errors above implies success.
