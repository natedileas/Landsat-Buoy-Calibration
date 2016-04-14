part_dir=$1
point_dir=$2

latString=$3
lonString=$4
jay=$5

nml=$6
gdalt=$7
skin_temp=$8

# tail
sed -e "s/longit/${lonString}/" -e "s/jay/${jay}/" -e "s/latitu/${latString}/" <$part_dir/tail.txt > $part_dir/newTail.txt            

# head
sed -e "s/nml/${nml}/" -e "s/gdalt/${gdalt}/" -e "s/tmp____/${skin_temp}/" <$part_dir/head.txt > $part_dir/newHead.txt
                  
# concatenate
headFile=$part_dir/newHead.txt
tailFile=$part_dir/newTail.txt
tempLayers=$part_dir/tempLayers.txt
newFile=$point_dir/tape5
            
cat $headFile $tempLayers $tailFile > $newFile

rm  $part_dir/newHead.txt
rm  $part_dir/newTail.txt