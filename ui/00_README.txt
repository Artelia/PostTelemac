Delete the line in properties.ui : 
  <include location="../resources.qrc"/>

in

"
 <resources>
  <include location="../resources.qrc"/>
 </resources>

otherwise it will not work..