<?php
/*
 * Copyright 2016 The Anonymous Press, Inc.
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

// This script runs the tracking number updater on all files on the warehouse server, then deletes the files from the server

require_once('config.php');
$ftp_path = $outgoing_ftp_path;

set_time_limit(1200);

if(!$ftp = ftp_connect($ftp_host)) die(var_dump(error_get_last()));
if(!ftp_login($ftp,$ftp_user,$ftp_pass)) die(var_dump(error_get_last()));
ftp_pasv($ftp,true);
if(!ftp_chdir($ftp,$ftp_path)) die(var_dump(error_get_last()));

$filenames = array_filter(ftp_nlist($ftp,'.'),function($v){return substr($v,-4)==='.txt';});

foreach($filenames as $file){
	ob_start();
	if(!ftp_get($ftp, "php://output", $file, FTP_BINARY)) var_dump(error_get_last());
	$input = ob_get_clean();
	//var_dump($input);
	file_put_contents('tracking/'.date('Y-m-d HiO').'.csv',$input); //save input data
	var_dump($input); //print input data
	include 'tracking.php';
	if(!ftp_delete($ftp,$file)) var_dump(error_get_last());
}



if(count($responses)>0){
	$p="Enter a response ID to output response, a filename to output responses (".number_format(strlen($printr))." bytes) to a text file, or 'exit':\r\n";
	echo $p;
	while($l=fgets(STDIN)){
		if(strtolower(trim($l))==='exit') die;
		if(preg_match('/^([0-9]+)$/',trim($l),$matches)){
			echo "\r\n\r\n".$responses[intval($matches[1])]."\r\n\r\n".$p;
		}
		else{
			echo number_format(file_put_contents(trim($l),$printr))." bytes written to ".__DIR__.DIRECTORY_SEPARATOR.trim($l)."\r\n";
			break;
		}
	}
}
