<?php

//Sean Gillen / Anonymous Press
//Last updated: 2017-02-12

$version = 1;
$secureURL = 'anonpress.net';
$privateKey = '';
$token = '';

$apiBaseURL = "https://apirest.3dcart.com/3dCartWebAPI/v$version/";

$newOrderStatus = 1;
$shippedOrderStatus = 4;
$holdOrderStatus = 6;

$verbose = true;

if(!isset($num_requests)) $num_requests = 0;

$timeout = 30;
$apiheader = array(
	'Content-Type: application/json;charset=UTF-8',
	'Accept: application/json',
	'SecureUrl: ' . $secureURL,
	'PrivateKey: ' . $privateKey,
	'Token: '. $token,
);

set_time_limit(300);
if(php_sapi_name()=="cli"){
	set_time_limit(1800);
	echo "CLI interface detected. Time limit set to 30 minutes.\n";
}
else echo "Time limit set to 5 minutes.\n";


$responses = array();

function get($url,$params){
	global $apiBaseURL, $apiheader, $verbose, $num_requests;
	if($num_requests > 45) {
		if($verbose) echo "More than 45 requests. Sleeping for 500 ms.";
		usleep(500000);
	}

	$startTime = microtime(true);
	if($verbose) echo @array_shift(debug_backtrace())["line"].": GET $url\r\n";

	$ch = curl_init($apiBaseURL.$url.'?'.http_build_query($params));
	curl_setopt($ch, CURLOPT_HTTPHEADER, $apiheader);

	curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
	curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

	$response = curl_exec($ch);
	$num_requests++;

	$runtime = number_format(microtime(true) - $startTime,3);
	if($verbose) outputResponse($response,$runtime);

	return $response===false?false:json_decode($response,true);
}

function put($url,$urlparams,$bodyparams,$post = false){
	global $apiBaseURL, $apiheader, $verbose, $debug, $num_requests;
	if($num_requests > 45) {
		if($verbose) echo "More than 45 requests. Sleeping for 500 ms.";
		usleep(500000);
	}

	$startTime = microtime(true);
	if($verbose) echo @array_shift(debug_backtrace())["line"].($post?': POST':': PUT')." $url\r\n";

	if($debug) {
		echo "DISABLED\r\n";
		return [false];
	}

	$data = json_encode($bodyparams);

	$ch = curl_init($apiBaseURL.$url.'?'.http_build_query($urlparams));
	curl_setopt($ch, CURLOPT_HTTPHEADER, array_merge($apiheader,array("Content-Length: ".strlen($data))));
	curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
	curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

	if($post) curl_setopt($ch, CURLOPT_POST, 1);
	else curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'PUT');
	curl_setopt($ch, CURLOPT_POSTFIELDS, $data);

	$response = curl_exec($ch);
	$num_requests++;

	$runtime = number_format(microtime(true) - $startTime,3);
	if($verbose) outputResponse($response,$runtime);

	return $response===false?[false]:json_decode($response,true);
}



function outputResponse($response,$time){
	global $errors, $warnings, $responses;

	if($response === false){
		echo "FAILED in $time seconds\r\ncURL error ";
		echo curl_errno($ch).": ".curl_error($ch)."\r\n";
		$errors++;
		return true;
	}


		$responses[] = $response;
		$responseid = count($responses)-1;

	echo "Succeeded in $time seconds\r\n";
	$decodedResponse = json_decode($response,true);
	if((isset($decodedResponse[0]["Status"]) && $decodedResponse[0]["Status"][0]!=="2") || (count($decodedResponse)===1 && count($decodedResponse)[0]===1) || !$decodedResponse){
		echo "WARNING: Response was: $response\r\n";
		if(php_sapi_name()=='cli') echo "(id $responseid)\r\n";
		$warnings++;
	}
	elseif(strlen(addcslashes($response,"\r\n")) <= 240){
		echo "Response was: $response\r\n";
		if(php_sapi_name()=='cli') echo "(id $responseid)\r\n";
	}
	elseif(php_sapi_name()=='cli'){ //not $cli so this works on interactive shells only
		echo "Response was ".strlen($response)." bytes (id $responseid)\r\n";
	}
	else{
		$gzippedResponse = base64_encode(gzcompress($response,9));
		echo "Response was";
		echo strlen($gzippedResponse)<=240?" (gzipped): $gzippedResponse\r\n":" ".strlen($response)." bytes\r\n";
	}

	echo "\r\n";
	return true;
}

function human_bytes($bytes, $decimals = 2) {
	if($bytes < 1024) return $bytes." bytes";
	$sz = 'BkMGTP';
	$factor = floor((strlen($bytes) - 1) / 3);
	return @sprintf("%.{$decimals}f", $bytes / pow(1024, $factor)) . " ".@$sz[$factor]."iB";
}

function return_bytes($val) {
    $val = trim($val);
    $last = strtolower($val[strlen($val)-1]);
    switch($last) {
        // The 'G' modifier is available since PHP 5.1.0
        case 'g':
            $val *= 1024;
        case 'm':
            $val *= 1024;
        case 'k':
            $val *= 1024;
    }

    return $val;
}


function f($errorNumber, $errorMessage, $errorFile, $errorLine, $errorContext) {
	if(error_reporting()) {
		global $phpMessages;
		$phpMessages++;
		echo "PHP message: $errorFile:$errorLine: [$errorNumber] $errorMessage; context: ";
		var_dump($errorContext);
	}
	return false;
}
