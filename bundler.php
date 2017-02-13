<?php

//Sean Gillen / Anonymous Press
//Last updated: 2017-02-12

if(isset($argv[1])) $in=$argv[1]; //For testing.

require_once('import_validated_orders.php'); //Generate input file from validated orders using 3dcart API.

if(!isset($in)) $in = 'input.csv';
if(!isset($out)) $out = 'incomingorders.csv';

echo "Input file: $in\r\n";

$IgnoreSKUs = array(); //Lines containing these SKUs will be removed

$BundleSKUs = array(						//Lines containing these SKUs will be bundled
);
$RemoveColumns = array('weight','unitprice','oi.weight','unitcost','itemamount','itemname','itemShipCost');
											//All other SKUs will be passed through without modification
											
$ShippingColumn = 'shipmethod';
$ShippingMethods = array(					//Values containing matches for the regular expressions on the left will be replaced with the values on the right. Others will be passed through.
	'/Priority/i' => 'Priority Mail',
	'/Media/i' => 'Media Mail'
);

$path = dirname(__FILE__).'/';

if(!file_exists($path.$in)){
	die("No input file was sent to the server by 3dcart. This may indicate that no orders are marked as new, or that something is broken on the 3dcart end.");
}

$InputFile = fopen($path.$in,'r');
$OutputFile = fopen($path.$out,'w');

								
$header = fgetcsv($InputFile); //Get CSV header


foreach($RemoveColumns as &$name){
	$name = array_search($name,$header); //Find column numbers for columns to remove
	if($name!==FALSE) unset($header[$name]); //Clear unneeded cells from header if the name matched a name in the header
}
$header = array_values($header); //Remove empty cells from header

$SKUColumn = array_search('itemid',$header); //Find column numbers for SKU and quantity columns
$QtyColumn = array_search('numitems',$header);
$ShippingColumn = array_search($ShippingColumn,$header); //Find column number for shipping method
$OrderColumn = array_search('ordernumber',$header);
$CouponColumn = array_search('Coupon',$header);
$ZipColumn = array_search('Zip',$header); //Zip column for ZIP+4 shim

function removecol($row,$col){
	if($col!==FALSE) unset($row[$col]);
	return array_values($row);
}

fputcsv($OutputFile,removecol($header,$CouponColumn)); //Copy CSV header to output file

$InputRows = array();
while($row = fgetcsv($InputFile)) $InputRows[]=$row; //Copy CSV rows into $InputRows[]

$CurrentOrder = ""; $CurrentSKU = ""; //Starting values
foreach($InputRows as $rownum=>&$row){ //Consolidate rows with same order number and SKU
	
	foreach($RemoveColumns as $num){if($num!==FALSE) unset($row[$num]);} //Clear unneeded cells from row if the name matched a name in the header
	$row=array_values($row); //Remove unneeded cells from row
	
	if($row[$OrderColumn] === $CurrentOrder && $row[$SKUColumn] === $CurrentSKU){ //If current row matches previous row
		$target = $rownum;
		$row[$OrderColumn] = "DELETE"; //Mark as redundant
		while(($InputRows[$target][$OrderColumn] !== $CurrentOrder || $InputRows[$target][$SKUColumn] !== $CurrentSKU) && $target > 0) $target--; //Find target row (first row with matching information)
		if($target<0) die('PANIC');
		$InputRows[$target][$QtyColumn] += $row[$QtyColumn]; //Add quantity to target row
	}
	else{
		$CurrentOrder = $row[$OrderColumn];
		$CurrentSKU = $row[$SKUColumn];
	}
}
$InputRows = array_values($InputRows);

foreach(array_keys($InputRows) as $key){ //Remove rows marked for deletion
	if($InputRows[$key][$OrderColumn] === "DELETE") unset($InputRows[$key]);
}
$InputRows = array_values($InputRows);


foreach($InputRows as &$row){ //Iterate through rows
	
	$sku = $row[$SKUColumn]; //Single item SKU
	$ItemQty = $row[$QtyColumn]; //Remaining quantity not yet output to output file
	
	if(array_search($sku,$IgnoreSKUs)!==FALSE) continue; //Skip rows containing ignored SKUs
	if(preg_match('/^ebay$/i',$row[$CouponColumn])) continue; //Skip rows for ebay orders
	
	foreach($ShippingMethods as $from=>$to) { //Iterate through possible shipping methods
		if(preg_match($from,$row[$ShippingColumn])){ //If shipping method matches
			$row[$ShippingColumn] = $to; //replace shipping method
			break;
		}
	}
	
	//ZIP+4 shim
	str_replace("-","",$row[$ZipColumn]);
	
	if(!isset($BundleSKUs[$sku])){ //If no bundle SKUs are available
		fputcsv($OutputFile,removecol($row,$CouponColumn)); //Copy row to output file unmodified
		continue;                  //to next row
	}
	
	//Below code will only be executed for input rows with SKUs for which bundle SKUs are available
	
	$OutputSKUs = $BundleSKUs[$sku]; //get SKUs for bundles
	$OutputSKUs[1] = $sku; //add SKU for single items
	
	krsort($OutputSKUs, SORT_NUMERIC); //largest bundles first	
	foreach($OutputSKUs as $SKUQty=>$OutputSKU) { //Each output SKU: $SKUQty = quantity in each bundle, $OutputSKU = SKU for bundle
		if($ItemQty >= $SKUQty){ //If order is larger than bundle
			$OutputRow = $row; //Make a copy of the input row
			$OutputRow[$SKUColumn] = $OutputSKU; //Change SKU in output row to bundle SKU
			$NumBundles = floor($ItemQty/$SKUQty); //Divide remaining items by bundle quantity and round down
			$OutputRow[$QtyColumn] = $NumBundles;
			fputcsv($OutputFile,removecol($OutputRow,$CouponColumn)); //Copy modified row to output file
			$ItemQty -= $SKUQty*$NumBundles; //Subtract accounted-for items from remaining total
		}
	}
}