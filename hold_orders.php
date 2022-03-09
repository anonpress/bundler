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

//This will mark all orders in file $path.$in or command line argument as "Hold" in the 3dcart database unless they contain unshipped items matching the SKUs in $IgnoreSKUs

require_once('3dapi.php');
$verbose = true;
//$debug = true;

echo "Marking transmitted orders as Hold.\r\n";

if(isset($argv[1]) && !function_exists("removecol")) include('bundler.php'); //run from command line for testing

if(!isset($in)){
	if(isset($argv[1])) $in=$argv[1];
	else $in='input.csv';
}
$InputFile = fopen($path.$in,'r');


$csvHeader = fgetcsv($InputFile); //Get CSV header
$OrderColumn = array_search('OrderNumber',$csvHeader);
$orders = array();
while($orderRow = fgetcsv($InputFile)) if(array_search($orderRow[$OrderColumn],$orders) === FALSE) $orders[] = $orderRow[$OrderColumn]; //populate $orders with invoice numbers for transmitted orders

foreach($orders as $invoicenum){
	$order = get('Orders',array('invoicenumber'=>$invoicenum));
	if(count($order) === 1) {
		echo "Order $invoicenum\r\n";
		$order = $order[0];
		foreach($order["OrderItemList"] as $orderItem)
			if(array_search($orderItem["ItemID"],$IgnoreSKUs) !== FALSE && array_search($orderItem["ItemID"],$DisregardSKUs) === FALSE)
				foreach($order["ShipmentList"] as $shipment)
					if($shipment["ShipmentID"] === $orderItem["ItemShipmentID"] && $shipment["ShipmentOrderStatus"] !== $shippedOrderStatus)
						continue 3; //Skip orders with unshipped non-warehouse items
		put('Orders/'.$order["OrderID"],array('orderid'=>$order["OrderID"]),array("OrderStatusID"=>$holdOrderStatus));
	}
	else echo "No order found for invoice $invoicenum.\r\n";
}
