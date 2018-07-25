<?php

//Tracking Number Updater
//Sean Gillen / Anonymous Press
//Last updated: 2018-07-25 13:08

$num_requests = 0;
require_once('3dapi.php');
set_time_limit(600);

$inputFile = 'input.csv';
if(isset($argv[1])) $inputFile = $argv[1];
$inputCols = 16;
$invNumCol = 0;
$trackingCol = 8;
$SKUCol = 11;
$qtyCol = 13;
$dateCol = 10;

$failsafe = true; //this will result in longer run times and more requests, but everything seems to break without it
$debug = false; //disables PUT and POST requests
if(isset($argv[1]) && isset($argv[2]) && $argv[2] === "debug") $debug = true;

$startTime = microtime(true);
$errors = 0;
$warnings = 0;
$phpMessages = 0;

set_error_handler('f', E_ERROR | E_WARNING | E_PARSE);

$cli = substr(php_sapi_name(), 0, 3) == 'cli' || empty($_SERVER['REMOTE_ADDR']);
if(!$cli){
	echo '<pre>';
	ob_start();
}


if(!isset($input)) $input = file_get_contents($inputFile);
$input = str_replace("\r","\n",$input);
$input = str_getcsv($input,"\n");
foreach($input as $line=>&$row){
	if($line === 0) continue;

	$row = str_getcsv($row);
	if(count($row)!==$inputCols) continue;

	$invoicenum = $row[$invNumCol];
	$tracking = $row[$trackingCol];
	$item = $row[$SKUCol];
	$qty = intval($row[$qtyCol]);
	$shipDate = date('m/d/Y',strtotime($row[$dateCol]));

	echo "\r\n\r\n\r\n\r\nLine $line: Invoice $invoicenum - $qty*$item - $tracking\r\n\r\n";
	if(php_sapi_name()!='cli') ob_start();

	$order = get('Orders',array('invoicenumber'=>$invoicenum))[0];

	if(preg_match('/^(.+)[Xx]([0-9]+)$/',$item,$matches)){ //debundle warehouse data
		$item = $matches[1];
		$qty *= $matches[2];
	}

	$shipmentID; $newShipmentID = false;
	$allMatch = true;
	$remainingQty = (int) $qty;

	//var_dump($order);

	foreach($order["OrderItemList"] as &$orderItem){
		foreach($order["ShipmentList"] as $orderShipment){
			if ($orderShipment["ShipmentID"] == $orderItem["ItemShipmentID"]
				&& (
					$orderShipment["ShipmentOrderStatus"] === $shippedOrderStatus
					|| $orderShipment["ShipmentTrackingCode"] !== ""
				) && count($order["ShipmentList"])>1 && count($order["OrderItemList"])>1
			) {
				continue 2; //if line has already been marked as shipped, do not process
			}
		}
		if(trim(strtoupper($orderItem["ItemID"])) === trim(strtoupper($item)) && $remainingQty > 0){ //If SKU matches and there are some left to mark as shipped
			if(intval($orderItem["ItemQuantity"]) <= intval($remainingQty)){ //If entire line has been shipped
				$remainingQty -= intval($orderItem["ItemQuantity"]);
				$orderItem["ItemShipmentID"] = &$shipmentID;
			}
			else{ //If part of line has been shipped
				$allMatch = false;
				$newItem = $orderItem; //duplicate item
				unset($newItem["ItemIndexID"]); //next available item id
				$newItem["ItemQuantity"] = intval($orderItem["ItemQuantity"] - $remainingQty);
				$newItem["ItemShipmentID"] = &$newShipmentID; //move remaining items to new shipment
				$newShipmentID = true; //new shipment is needed
				$orderItem["ItemQuantity"] = intval($remainingQty);
				$orderItem["ItemShipmentID"] = &$shipmentID;
				$order["OrderItemList"][] = $newItem; //add item to order (will be put to 3dcart later)
				$remainingQty = 0;
			}
		}
		else{ //If line has not been shipped (SKU does not match or none left to mark as shipped)
			$allMatch = false;
			$orderItem["ItemShipmentID"] = &$newShipmentID; //move to new shipment
			$newShipmentID = true; //new shipment is needed
		}
	} unset($orderItem);

	foreach($order["ShipmentList"] as &$shipment){ //3dcart sometimes breaks itself on this for some reason
		if(!isset($shipment["ShipmentPhone"])||$shipment["ShipmentPhone"]==="") $shipment["ShipmentPhone"] = "0000000000";
	} unset($shipment);

	foreach($order["ShipmentList"] as $shipment){
		if($shipment["ShipmentTrackingCode"] === $tracking) { //If tracking number matches an original shipment
			//echo "using existing shipment ".$shipment["ShipmentID"]." with tracking code ".$shipment["ShipmentTrackingCode"];
			$shipmentID = $shipment["ShipmentID"];
			break;
		}
	}
	if(!isset($shipmentID)){ //if no existing shipment matched the tracking number
		if(count($order["ShipmentList"]) === 1 && ($order["ShipmentList"][0]["ShipmentOrderStatus"] !== $shippedOrderStatus || $order["OrderStatusID"] !== $shippedOrderStatus)) { //if only one shipment and it is unshipped
			$shipmentID = $order["ShipmentList"][0]["ShipmentID"]; //generally 0
		}
		else {
			foreach($order["ShipmentList"] as $shipment){ //Find first shipment in order that has no associated items
				foreach($order["OrderItemList"] as $orderItem) {
					if($orderItem["ItemShipmentID"] == $shipment["ShipmentID"]) {
						//echo "continuing: shipment ".$shipment["ShipmentID"];
						continue 2; //Shipment contains an item
					}
				}
				//Shipment contains no item
				//echo "using existing shipment ".$shipment["ShipmentID"];
				$shipmentID = $shipment["ShipmentID"];
				break;
			}
		}
	}
	while($newShipmentID===true){ //Find next available shipment ID
		foreach($order["ShipmentList"] as $shipment){ //Check existing shipments for unshipped shipments that will not be marked shipped
			echo "Shipment: ".$shipment["ShipmentID"]."\n";
			if($shipment["ShipmentOrderStatus"] === $shippedOrderStatus || $shipment["ShipmentTrackingCode"] !== "") {
				echo "continue\n";
				continue; //shipment is shipped
			}
			echo "\$shipmentID = $shipmentID\n";
			if(isset($shipmentID) && $shipmentID!=0 && $shipment["ShipmentID"] != $shipmentID) { //Shipment will not be marked shipped
				echo "use shipment\n";
				$newShipmentID = $shipment["ShipmentID"]; //use this existing shipment as the "new shipment"
				break; //stop looking
			}
			//Shipment is unshipped but will be marked shipped: keep looking (continue)
		}
		if($newShipmentID===true){ //If the above method failed to find an empty shipment that will not be filled to use as the new shipment, create a new shipment.
			//Create new shipment
			$newShipment = end($order["ShipmentList"]); //Duplicate last shipment
			$newShipment["ShipmentID"] = null; //next available shipment id
			$newShipment["ShipmentLastUpdate"] = date('c');
			$newShipment["ShipmentOrderStatus"] = $newOrderStatus;
			$newShipment["ShipmentWeight"] = 0; //Shipment weights become individually meaningless, but we need the sum to stay the same or 3dcart starts recalculating shipping for some reason
			$newShipment["ShipmentCost"] = 0; //same as weight
			$newShipment["ShipmentNumber"]++;
			foreach(array("ShipmentShippedDate","ShipmentTrackingCode","ShipmentTax","ShipmentWeight") as $field){
				$newShipment[$field] = "";
			}
			$newShipmentID = put("Orders/".$order["OrderID"]."/Shipments",array('orderid'=>$order["OrderID"]),$newShipment,true);
			if(isset($newShipmentID[1])){
				//echo "using shipment id ".$newShipmentID[1];
				$shipmentID = $newShipmentID[0]["Value"]; //If the id of the warehouse shipment changed
			}
			$newShipmentID = $newShipmentID[count($newShipmentID)-1]["Value"];
			if(!isset($shipmentID)||$shipmentID==0){
				$shipmentID = $newShipmentID; //If this shipment is the warehouse shipment
				//echo "using new shipment ".$shipmentID;
			}
			if($shipmentID==$newShipmentID&&!$allMatch) //If another new shipment is required
				$newShipmentID = true; //loop back to beginning and look for unshipped shipments that will not be marked as shipped
		}
	}
	$shipmentData = array(
		'ShipmentTrackingCode'=>$tracking,
		'ShipmentLastUpdate'=>date('c'),
		'ShipmentShippedDate'=>$shipDate,
		'ShipmentBoxes'=>1
	);

	put("Orders/".$order["OrderID"]."/Shipments/".$shipmentID,array('orderid'=>$order["OrderID"],'shipmentid'=>$shipmentID),$shipmentData); //Update shipment in 3dcart
	put("Orders/".$order["OrderID"]."/Shipments/".$shipmentID,array('orderid'=>$order["OrderID"],'shipmentid'=>$shipmentID),array('ShipmentOrderStatus'=>$shippedOrderStatus)); //Separate this out to work around a 3dcart bug in which the first shipment within an Unpaid order cannot be set to Shipped w/o first being set to New

	//var_dump($order); //debug code

	//put item list
	if(!isset($failsafe)||$failsafe){
		foreach($order["OrderItemList"] as &$orderItem){
			if(!isset($orderItem["ItemIndexID"])) //If item is new
				$orderItem["ItemIndexID"] = end(put("Orders/".$order["OrderID"]."/Items",array('orderid'=>$order["OrderID"]),$orderItem,true))["Value"];
			else put("Orders/".$order["OrderID"]."/Items/".$orderItem["ItemIndexID"],array('orderid'=>$order["OrderID"],'itemindexid'=>$orderItem["ItemIndexID"]),$orderItem); //If item is updated or unchanged
		} unset($orderItem);
	}
	else put("Orders/".$order["OrderID"]."/Items",array('orderid'=>$order["OrderID"]),$order["OrderItemList"]);

	//get updated order details
	$expectedTotal = $order["OrderAmount"];
	$order = get('Orders',array('invoicenumber'=>$invoicenum))[0];
	if($order["OrderAmount"] !== $expectedTotal) {
		echo "ERROR: Order amount has changed from \$".number_format($expectedTotal)." to \$".number_format($order["OrderAmount"])."\r\n\r\n";
		$errors++;
	}

	$allShipped = true;
	$emptyShipments = false;
	//Remove empty shipments
	foreach($order["ShipmentList"] as $key=>$orderShipment){
		foreach($order["OrderItemList"] as $orderItem){
			if($orderShipment["ShipmentID"] == $orderItem["ItemShipmentID"]) continue 2; //shipment contains an item - continue to next shipment
		}
		//Below code will execute only if shipment contains no items
		unset($order["ShipmentList"][$key]); //remove from shipment list
		$emptyShipments = true;
	}
	$order["ShipmentList"] = array_values($order["ShipmentList"]);
	//Check for unshipped items
	foreach($order["ShipmentList"] as $orderShipment){
		if($orderShipment["ShipmentOrderStatus"] !== $shippedOrderStatus){ //unshipped item
			$allShipped = false;
			break; //no need to continue checking
		}
	}

	//if($emptyShipments) var_dump(put("Orders/".$order["OrderID"]."/Shipments",array('orderid'=>$order["OrderID"]),$order["ShipmentList"])); //Remove empty shipments in 3dcart - doesn't work for some reason

	if($order["OrderStatusID"] !== $allShipped?$shippedOrderStatus:$holdOrderStatus) put("Orders/".$order["OrderID"],array('orderid'=>$order["OrderID"]),array("OrderStatusID"=>$allShipped?$shippedOrderStatus:$holdOrderStatus)); //Update order status in 3dcart to reflect $allShipped

	if(php_sapi_name()!='cli') echo "\t".trim(str_replace("\n","\n\t",ob_get_clean()))."\r\n\r\n";

	unset($shipmentID, $newShipmentID);
}

if(!$cli) $log = ob_get_clean();
else echo "\r\n--------------------------\r\n";

$runtime = number_format(microtime(true) - $startTime,3);
$printr=print_r($responses,true);
$memory=array(memory_get_peak_usage(),return_bytes(ini_get('memory_limit')));
$memory=human_bytes($memory[0],1)." / ".human_bytes($memory[1],0)." (".number_format($memory[0]/$memory[1]*100,1)."%)";

echo "\r\nCompleted in $runtime seconds\r\n$phpMessages PHP messages, $errors errors, $warnings warnings\r\nMemory usage: $memory\r\n\r\n--------------------------\r\n\r\n";
if(!$cli) echo trim($log);

if(!$cli&&strpos($log,'gzipped')){
	$dir = implode('/',array_slice(explode('/',$_SERVER['REQUEST_URI']),0,-1));
	echo "\r\n\r\n\r\nGzip decoder is at <a target=\"_blank\" href=\"$dir/ungzip.php\">ungzip.php</a>\r\nOr run PHP CLI: php -r\"\$p=PHP_EOL.'Paste gzipped string (right-click) or enter \'exit\': '.PHP_EOL;echo\$p;while(\$l=fgets(STDIN))echo strtolower(trim(\$l))==='exit'?die:PHP_EOL.gzuncompress(base64_decode(\$l)).PHP_EOL.PHP_EOL.\$p;\"\r\n";
}

if(!$cli) echo '</pre>';

unset($input);
?>
