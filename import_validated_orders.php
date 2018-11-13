<?php

//This script creates a csv input file for the bundler from orders that have been marked as having validated addresses in 3dcart, and stores the filename in $in
//Header:
//OrderNumber,ShipMethod,Comments,FirstName,LastName,Company,Address1,Address2,City,State,Zip,Phone,Email,Coupon,itemid,itemname,numitems,unitprice,weight,unitcost,itemamount
//Sean Gillen / Anonymous Press
//Last updated: 2018-11-13

$filename = "input_".time().".csv";
$csv = fopen($filename,"x"); //Create and open $filename

fwrite($csv, "OrderNumber,ShipMethod,Comments,FirstName,LastName,Company,Address1,Address2,City,State,Zip,Phone,Email,Coupon,itemid,numitems\r\n"); //Write csv header
//            0           1          2        3         4        5       6        7        8    9     10  11    12    13     14     15

require_once('3dapi.php');
$newOrders = getOrders($newOrderStatus);

foreach($newOrders as $order){
	if(strtoupper(trim(strtok($order["CustomerComments"],"\n"))) !== "ADDRESS VALIDATED"){
		echo "Order skipped due to non-validated address: ".$order["InvoiceNumber"]."\r\n";
		continue;
	}

	foreach($order["OrderItemList"] as $OrderItem){

		$values = array();
		$values[0] = $order["InvoiceNumber"];
		$values[1] = $order["ShipmentList"][0]["ShipmentMethodName"];
		$values[2] = '';
		$values[3] = $order["ShipmentList"][0]["ShipmentFirstName"];
		$values[4] = $order["ShipmentList"][0]["ShipmentLastName"];
		$values[5] = $order["ShipmentList"][0]["ShipmentCompany"];
		$values[6] = $order["ShipmentList"][0]["ShipmentAddress"];
		$values[7] = $order["ShipmentList"][0]["ShipmentAddress2"];
		$values[8] = $order["ShipmentList"][0]["ShipmentCity"];
		$values[9] = $order["ShipmentList"][0]["ShipmentState"];
		$values[10] = $order["ShipmentList"][0]["ShipmentZipCode"];
		$values[11] = $order["ShipmentList"][0]["ShipmentPhone"];
		$values[12] = $order["ShipmentList"][0]["ShipmentEmail"];
		if(!$values[12]) $values[12] = $order["BillingEmail"];
		$values[13] = $order["PromotionList"][0]["Coupon"];
		$values[14] = $OrderItem["ItemID"];
		$values[15] = $OrderItem["ItemQuantity"];

		fputcsv($csv,$values);

	}
}

fclose($csv);

$in = $filename;
