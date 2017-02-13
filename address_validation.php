<?php

//Address validation script
//Check 3dcart for new orders that have not been validated, and validate said orders
//Sean Gillen / Anonymous Press
//Last updated: 2017-02-12

require_once('3dapi.php');
$mailto = ""; //production
//$mailto = ""; //testing

$usps_user = "";

//Get list of new orders from 3dcart.

$newOrders = get('Orders',array('orderstatus'=>$newOrderStatus));

function failureEmail($ordernum, $message){
	global $mailto;

	//For email
	$subject = "Order $ordernum - Address validation failed";
	$body = "Order $ordernum\r\n$message";
	if(!mail($mailto, $subject, $body)) echo "Sending email to $mailto failed!\n";

	//For logging
	echo "\nEmail to $mailto: \n$body\n\n";
}

function validateAddress($addr1in, $addr2in, $cityin, $statein, $zipin){ //Send address to USPS, return validated address or FALSE for error.
	global $usps_user;

	//https://secure.shippingapis.com/ShippingAPI.dll?API=APINAME&XML=<APINAMERequest USERNAME='your account'><tag>data here</tag><tag1>data</tag1></APINAMERequest>

	if(strlen(trim($zipin)) >= 5){
		$zip5 = substr(trim($zipin),0,5);
		if(strlen(trim($zipin)) >= 9){
			$zip4 = substr(trim($zipin),-4);
		}
		else $zip4 = '';
	} else $zip5 = '';

	$xml = new SimpleXMLElement('<AddressValidateRequest/>');
	$xml->addAttribute('USERID',$usps_user);
	$address = $xml->addChild('Address');
	$address->addAttribute('ID','0');
	$address->addChild('Address1',trim($addr2in));
	$address->addChild('Address2',trim($addr1in)); //USPS swaps address 2 and 1 for some reason
	$address->addChild('City',trim($cityin));
	$address->addChild('State',trim($statein));
	$address->addChild('Zip5',$zip5);
	$address->addChild('Zip4',$zip4);

	$xml = $xml->asXML();
	$xml = trim(substr($xml, strpos($xml, '?>') + 2)); //Remove XML header
	echo "\nRequest XML: $xml\n";

	$data = array("API"=>"Verify","XML"=>$xml);

	$ch = curl_init('https://secure.shippingapis.com/ShippingAPI.dll?'.http_build_query(array('API'=>"Verify",'XML'=>$xml)));
	$apiheader = array();
	curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
	curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);

	$response = curl_exec($ch);
	echo "\nResponse XML: $response\n";

	if(strpos($response, "<Error" !== FALSE)) return FALSE;

	$response = new SimpleXMLElement($response);
	$response = $response->Address;
	$address = array(
		'ShipmentAddress' => (string) $response->Address2,
		'ShipmentAddress2' => (string) $response->Address1,
		'ShipmentCity' => (string) $response->City,
		'ShipmentState' => (string) $response->State,
		'ShipmentZipCode' => ((string) $response->Zip5).((string) $response->Zip4),
	);
	var_dump($address);

	return $address;
}

//$newOrders = array($newOrders[0]); //For testing, only process one order.

foreach($newOrders as &$order){

	//var_dump($order);

	echo "Order ".$order["InvoiceNumber"].": ";
	$validationStatus = strtoupper(trim(strtok($order["CustomerComments"],"\n")));
	//echo $validationStatus."\n";

	if($validationStatus === "ADDRESS VALIDATED"){
		echo "Address already validated; skipping.\n";
		continue;
	}
	if($validationStatus === "ADDRESS VALIDATION FAILED"){
		echo "Address validation failed; notice already sent. Skipping.\n";
		continue;
	}

	/*
	Order address:
	$order["ShipmentList"][0]["ShipmentAddress"]
	$order["ShipmentList"][0]["ShipmentAddress2"]
	$order["ShipmentList"][0]["ShipmentCity"]
	$order["ShipmentList"][0]["ShipmentState"] (as two letter abbreviation?)
	$order["ShipmentList"][0]["ShipmentZipCode"] (as whatever format it feels like)
	$order["ShipmentList"][0]["ShipmentCountry"] = "US"
	*/

	if($order["ShipmentList"][0]["ShipmentCountry"] !== "US"){
		failureEmail($order["InvoiceNumber"], "Country is not US, but ".$order["ShipmentList"][0]["ShipmentCountry"].". Order kept in New.");
		continue;
	}

	$successfullyValidated = false;

	//Validate address
	$validatedAddress = validateAddress($order["ShipmentList"][0]["ShipmentAddress"],$order["ShipmentList"][0]["ShipmentAddress2"],$order["ShipmentList"][0]["ShipmentCity"],$order["ShipmentList"][0]["ShipmentState"],$order["ShipmentList"][0]["ShipmentZipCode"]);
	if($validatedAddress !== FALSE) {
		foreach($order["ShipmentList"] as &$shipment){
			$shipment = array_merge($shipment, $validatedAddress);
		}
		$successfullyValidated = true;
		echo "\nAddress validated.\n";
	}


	if(!$successfullyValidated) {
		failureEmail($order["InvoiceNumber"], "The following address could not be validated: \n".$order["ShipmentList"][0]["ShipmentAddress"]."\n".(trim($order["ShipmentList"][0]["ShipmentAddress2"])!==""?$order["ShipmentList"][0]["ShipmentAddress2"]."\n":"").
			$order["ShipmentList"][0]["ShipmentCity"]." ".$order["ShipmentList"][0]["ShipmentState"]." ".$order["ShipmentList"][0]["ShipmentZipCode"]."\n\nThe order will remain in New until the first line of Customer Comments is changed to \"Address validated\".");
		$order["CustomerComments"] = "Address validation failed\r\nAfter checking address, change the above line to \"Address validated\"\r\n\r\n".$order["CustomerComments"];
	}
	else {
		$order["CustomerComments"] = "Address validated\r\n\r\n".$order["CustomerComments"];
	}

	//Update order address & internal comments
	put('Orders/'.$order["OrderID"],array("orderid"=>$order["OrderID"]),array("ShipmentList"=>$order["ShipmentList"], "CustomerComments"=>$order["CustomerComments"]));
}
