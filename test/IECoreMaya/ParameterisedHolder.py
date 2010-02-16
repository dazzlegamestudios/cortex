##########################################################################
#
#  Copyright (c) 2008-2009, Image Engine Design Inc. All rights reserved.
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#
#     * Neither the name of Image Engine Design nor the names of any
#       other contributors to this software may be used to endorse or
#       promote products derived from this software without specific prior
#       written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
#  IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
#  THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
#  PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
#  CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
#  EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
#  PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
#  PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
#  LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#  NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
##########################################################################

import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import unittest, MayaUnitTest
import os.path
import IECore
import IECoreMaya


class TestParameterisedHolder( unittest.TestCase ) :

	def testNode( self ):
		""" Test ParameterisedHolderNode """
		n = cmds.createNode( "ieParameterisedHolderNode" )
		h = IECoreMaya.FnParameterisedHolder( str(n) )
		self.assert_( h )

		p = IECore.ParticleMeshOp()

		h.setParameterised( p )

		p.parameters()["filename"] = "testValue"
		h.setNodeValue( p.parameters()["filename"] )
		pl = h.parameterPlug( p.parameters()["filename"] )
		v = IECoreMaya.FromMayaPlugConverter.create( pl, IECore.TypeId.StringData ).convert()
		self.assertEqual( v.value, "testValue" )

		cmds.setAttr( pl.name(), "testValue2", typ="string" )
		h.setParameterisedValue( p.parameters()["filename"] )
		self.assertEqual( p.parameters()["filename"].getValue().value, "testValue2" )


	def testParameterisedHolderSetReference( self ):
		""" Test multiple references to ieParameterisedHolderSet nodes """

		nodeType = "ieParameterisedHolderSet"

		nodeName = cmds.createNode( nodeType )

		cmds.file( rename = os.path.join( os.getcwd(), "test", "IECoreMaya", "reference.ma" ) )
		scene = cmds.file( force = True, type = "mayaAscii", save = True )

		cmds.file( new = True, force = True )
		cmds.file( scene, reference = True, namespace = "ns1" )
		cmds.file( scene, reference = True, namespace = "ns2" )

		cmds.file( rename = os.path.join( os.getcwd(), "test", "IECoreMaya", "referenceMaster.ma" ) )
		masterScene = cmds.file( force = True, type = "mayaAscii", save = True )

		cmds.file( masterScene, force = True, open = True )

		nodeName1 = "ns1:" + nodeName
		nodeName2 = "ns2:" + nodeName

		l = OpenMaya.MSelectionList()
		l.add( nodeName1 )
		l.add( nodeName2 )

		node1 = OpenMaya.MObject()
		l.getDependNode( 0, node1 )
		node2 = OpenMaya.MObject()
		l.getDependNode( 1, node2 )

		fn1 = OpenMaya.MFnDependencyNode( node1 )
		fn2 = OpenMaya.MFnDependencyNode( node2 )

		self.assert_( fn1.userNode() )
		self.assert_( fn2.userNode() ) # This failure is due to a Maya bug. When referencing the same scene twice, as an optimisation Maya will duplicate existing nodes instead of creating new ones. There is a bug in MPxObjectSet::copy() which gets exercised here. Setting the environment variable MAYA_FORCE_REF_READ to 1 will disable this optimisation, however.

	def testChangeDefault( self ) :
		""" Test that changing parameter defaults is correctly reflected in Maya attributes """

		def makeOp( defaultValue ) :

			class TestOp( IECore.Op ) :

				def __init__( self ) :

					IECore.Op.__init__( self, "Tests stuff",
						IECore.IntParameter(
							name = "result",
							description = "",
							defaultValue = 0
						)
					)

					self.parameters().addParameters(
						[
							IECore.Color3fParameter(
								name = "c",
								description = "",
								defaultValue = defaultValue
							),
						]
					)

			return TestOp()


		n = cmds.createNode( "ieParameterisedHolderNode" )
		h = IECoreMaya.FnParameterisedHolder( str(n) )
		self.assert_( h )

		p = makeOp( IECore.Color3f( 0, 0, 0 ) )
		h.setParameterised( p )
		dv = cmds.attributeQuery ( "parm_c", node = n, listDefault = True )
		self.assertEqual( dv, [ 0, 0, 0 ] )

		p = makeOp( IECore.Color3f( 1, 1, 1 ) )
		h.setParameterised( p )
		dv = cmds.attributeQuery ( "parm_c", node = n, listDefault = True )
		self.assertEqual( dv, [ 1, 1, 1 ] )

	def testDynamicParameters( self ) :

		fnPH = IECoreMaya.FnOpHolder.create( "holder", "maths/multiply", 2 )

		p = fnPH.getParameterised()[0]

		p.parameters().addParameter(

			IECore.IntParameter(
				"iAmDynamic",
				"",
				2
			)

		)

		fnPH.updateParameterised()

		self.assert_( cmds.objExists( fnPH.fullPathName() + ".parm_iAmDynamic" ) )
		plug = fnPH.parameterPlug( p["iAmDynamic"] )
		self.assertEqual( plug.partialName(), "parm_iAmDynamic" )
		self.assertEqual( plug.asInt(), 2 )

		plug.setInt( 3 )
		fnPH.setParameterisedValue( p["iAmDynamic"] )
		self.assertEqual( p["iAmDynamic"].getNumericValue(), 3 )

		plug.setInt( 4 )
		fnPH.setParameterisedValues()
		self.assertEqual( p["iAmDynamic"].getNumericValue(), 4 )

		p["iAmDynamic"].setNumericValue( 5 )
		fnPH.setNodeValue( p["iAmDynamic"] )
		self.assertEqual( plug.asInt(), 5 )

		p["iAmDynamic"].setNumericValue( 6 )
		fnPH.setNodeValues()
		self.assertEqual( plug.asInt(), 6 )

		p.parameters().removeParameter( p["iAmDynamic"] )
		fnPH.updateParameterised()
		self.assert_( not cmds.objExists( fnPH.fullPathName() + ".parm_iAmDynamic" ) )

	def testDynamicParametersDuplicate( self ) :

		fnPH = IECoreMaya.FnOpHolder.create( "holder", "maths/multiply", 2 )

		p = fnPH.getParameterised()[0]

		p.parameters().addParameter(

			IECore.IntParameter(
				"iAmDynamic",
				"iAmADescription",
				2
			)

		)

		fnPH.updateParameterised()

		dd = cmds.duplicate( fnPH.fullPathName() )[0]

		fnPH2 = IECoreMaya.FnParameterisedHolder( dd )
		p2 = fnPH2.getParameterised()[0]

		self.assert_( p2["iAmDynamic"].isInstanceOf( IECore.IntParameter.staticTypeId() ) )
		self.assertEqual( p2["iAmDynamic"].description, "iAmADescription" )
		self.assertEqual( p2["iAmDynamic"].defaultValue, IECore.IntData( 2 ) )
		self.assert_( not p2["iAmDynamic"].isSame( p["iAmDynamic"] ) )

		plug = fnPH2.parameterPlug( p2["iAmDynamic"] )
		self.assertEqual( plug.asInt(), 2 )

		p["iAmDynamic"].setNumericValue( 10 )
		p2["iAmDynamic"].setNumericValue( 20 )
		fnPH.setNodeValues()
		fnPH2.setNodeValues()
		self.assertEqual( fnPH.parameterPlug( p["iAmDynamic"] ).asInt(), 10 )
		self.assertEqual( fnPH2.parameterPlug( p2["iAmDynamic"] ).asInt(), 20 )

	def testDynamicParametersAddRemoveAndDuplicate( self ) :

		fnPH = IECoreMaya.FnOpHolder.create( "holder", "maths/multiply", 2 )

		p = fnPH.getParameterised()[0]

		p.parameters().addParameter(

			IECore.IntParameter(
				"iAmDynamic",
				"iAmADescription",
				2
			)

		)

		fnPH.updateParameterised()

		p.parameters().removeParameter( p["iAmDynamic"] )
		fnPH.updateParameterised()
		self.assert_( not cmds.objExists( fnPH.fullPathName() + ".parm_iAmDynamic" ) )
		self.assert_( not "iAmDynamic" in p.parameters() )

		dd = cmds.duplicate( fnPH.fullPathName() )[0]

		fnPH2 = IECoreMaya.FnParameterisedHolder( dd )
		p2 = fnPH2.getParameterised()[0]

		self.assert_( not cmds.objExists( fnPH2.fullPathName() + ".parm_iAmDynamic" ) )
		self.assert_( not "iAmDynamic" in p2.parameters() )

	def testDynamicParametersSaveAndLoad( self ) :

		fnPH = IECoreMaya.FnOpHolder.create( "holder", "maths/multiply", 2 )

		p = fnPH.getParameterised()[0]

		p.parameters().addParameter(

			IECore.IntParameter(
				"iAmDynamic",
				"iAmADescription",
				2
			)

		)

		fnPH.updateParameterised()

		cmds.file( rename = os.path.join( os.getcwd(), "test", "IECoreMaya", "dynamicParameters.ma" ) )
		scene = cmds.file( force = True, type = "mayaAscii", save = True )
		cmds.file( new = True, force = True )
		cmds.file( scene, open = True )

		fnPH = IECoreMaya.FnOpHolder( "holder" )
		p = fnPH.getParameterised()[0]

		self.assert_( cmds.objExists( fnPH.fullPathName() + ".parm_iAmDynamic" ) )
		plug = fnPH.parameterPlug( p["iAmDynamic"] )
		self.assertEqual( plug.partialName(), "parm_iAmDynamic" )
		self.assertEqual( plug.asInt(), 2 )
		self.assert_( p["iAmDynamic"].isInstanceOf( IECore.IntParameter.staticTypeId() ) )
		self.assertEqual( p["iAmDynamic"].description, "iAmADescription" )
		self.assertEqual( p["iAmDynamic"].defaultValue, IECore.IntData( 2 ) )

	def testDynamicParametersReload( self ) :

		fnPH = IECoreMaya.FnOpHolder.create( "holder", "maths/multiply", 1 )

		p = fnPH.getParameterised()[0]

		p.parameters().addParameter(

			IECore.IntParameter(
				"iAmDynamic",
				"iAmADescription",
				2
			)

		)

		fnPH.updateParameterised()
		fnPH.setOp( "maths/multiply", 2 )

		p = fnPH.getParameterised()[0]
		plug = fnPH.parameterPlug( p["iAmDynamic"] )
		self.assertEqual( plug.asInt(), 2 )
		self.assert_( p["iAmDynamic"].isInstanceOf( IECore.IntParameter.staticTypeId() ) )
		self.assertEqual( p["iAmDynamic"].description, "iAmADescription" )
		self.assertEqual( p["iAmDynamic"].defaultValue, IECore.IntData( 2 ) )

	def testEmptyDynamicCompoundParameters( self ) :

		fnPH = IECoreMaya.FnOpHolder.create( "holder", "maths/multiply", 1 )

		p = fnPH.getParameterised()[0]

		p.parameters().addParameter(

			IECore.CompoundParameter(
				"iAmDynamic",
				"andIAmACompoundParameter",
			)

		)

		fnPH.updateParameterised()

		dd = cmds.duplicate( fnPH.fullPathName() )[0]

		fnPH2 = IECoreMaya.FnParameterisedHolder( dd )
		p2 = fnPH2.getParameterised()[0]

		self.assert_( p2["iAmDynamic"].isInstanceOf( IECore.CompoundParameter.staticTypeId() ) )
		self.assert_( not p["iAmDynamic"].isSame( p2["iAmDynamic"] ) )
		self.assertEqual( len( p2["iAmDynamic"] ), 0 )
		self.assert_( not fnPH2.parameterPlug( p2["iAmDynamic"] ).isNull() )

	def testDynamicCompoundParametersWithDynamicChildren( self ) :

		fnPH = IECoreMaya.FnOpHolder.create( "holder", "maths/multiply", 1 )

		p = fnPH.getParameterised()[0]

		p.parameters().addParameter(

			IECore.CompoundParameter(
				"iAmDynamic",
				"andIAmACompoundParameter",
			)

		)

		p["iAmDynamic"].addParameter(

			IECore.IntParameter(
				"iAmDynamicToo",
				"iAmADescriptionToo",
				2
			)

		)

		fnPH.updateParameterised()
		self.assertEqual( fnPH.parameterPlug( p["iAmDynamic"]["iAmDynamicToo"] ).asInt(), 2 )

		dd = cmds.duplicate( fnPH.fullPathName() )[0]

		fnPH2 = IECoreMaya.FnParameterisedHolder( dd )
		p2 = fnPH2.getParameterised()[0]
		self.assertEqual( fnPH2.parameterPlug( p2["iAmDynamic"]["iAmDynamicToo"] ).asInt(), 2 )

	def testDynamicCompoundParametersWithDynamicChildrenAddedLater( self ) :

		fnPH = IECoreMaya.FnOpHolder.create( "holder", "maths/multiply", 1 )

		p = fnPH.getParameterised()[0]

		p.parameters().addParameter(

			IECore.CompoundParameter(
				"iAmDynamic",
				"andIAmACompoundParameter",
			)

		)

		fnPH.updateParameterised()

		p["iAmDynamic"].addParameter(

			IECore.IntParameter(
				"iAmDynamicToo",
				"iAmADescriptionToo",
				2
			)

		)

		fnPH.updateParameterised()
		self.assertEqual( fnPH.parameterPlug( p["iAmDynamic"]["iAmDynamicToo"] ).asInt(), 2 )

		dd = cmds.duplicate( fnPH.fullPathName() )[0]

		fnPH2 = IECoreMaya.FnParameterisedHolder( dd )
		p2 = fnPH2.getParameterised()[0]
		self.assertEqual( fnPH2.parameterPlug( p2["iAmDynamic"]["iAmDynamicToo"] ).asInt(), 2 )

	def testDirectSettingOfOp( self ) :
	
		class TestOp( IECore.Op ) :
		
			def __init__( self ) :
			
				IECore.Op.__init__( self,
					"",
					IECore.FloatParameter(
						"result",
						"",
						0.0
					),
				)
				
				self.parameters().addParameter(

					IECore.FloatParameter(
						"a",
						"",
						0.0
					)

				)
				
			def doOperation( self, operands ) :
			
				return IECore.FloatData( operands["a"].value )
				
		node = cmds.createNode( "ieOpHolderNode" )
		fnOH = IECoreMaya.FnParameterisedHolder( str( node ) )

		op = TestOp()
		fnOH.setParameterised( op )
	
		self.failUnless( cmds.objExists( node + ".result" ) )
		
		aAttr = fnOH.parameterPlugPath( op["a"] )

		cmds.setAttr( aAttr, 10 )
		self.assertEqual( cmds.getAttr( node + ".result" ), 10 )

		cmds.setAttr( aAttr, 20 )
		self.assertEqual( cmds.getAttr( node + ".result" ), 20 )


	def testLazySettingFromCompoundPlugs( self ) :
	
		class TestProcedural( IECore.ParameterisedProcedural ) :
		
			def __init__( self ) :
			
				IECore.ParameterisedProcedural.__init__( self, "" )
				
				self.parameters().addParameter(
				
					IECore.V3fParameter(
						"halfSize",
						"",
						IECore.V3f( 0 )
					)
				
				)
				
			def doBound( self, args ) :
			
				return IECore.Box3f( -args["halfSize"].value, args["halfSize"].value )
			
			def doRenderState( self, args ) :
			
				pass
					
			def doRender( self, args ) :
			
				pass
	
		node = cmds.createNode( "ieProceduralHolder" )
		fnPH = IECoreMaya.FnParameterisedHolder( str( node ) )
		
		p = TestProcedural()
		fnPH.setParameterised( p )
		
		self.assertEqual( cmds.getAttr( node + ".boundingBoxMin" ), [( 0, 0, 0 )] )
		cmds.setAttr( fnPH.parameterPlugPath( p["halfSize"] ), 1, 2, 3 )
		
		self.assertEqual( cmds.getAttr( node + ".boundingBoxMin" ), [( -1, -2, -3 )] )
	
	def testLazySettingFromArrayPlugs( self ) :
	
		class TestProcedural( IECore.ParameterisedProcedural ) :
		
			def __init__( self ) :
			
				IECore.ParameterisedProcedural.__init__( self, "" )
				
				self.parameters().addParameter( 
				
					IECore.SplineffParameter(
						"spline",
						"",
						defaultValue = IECore.SplineffData(
							IECore.Splineff(
								IECore.CubicBasisf.catmullRom(),
								(
									( 0, 1 ),
									( 0, 1 ),
									( 1, 0 ),
									( 1, 0 ),
								),
							),
						),
					),
				
				)
				
			def doBound( self, args ) :
			
				v = args["spline"].value.points()[0][1]
			
				return IECore.Box3f( IECore.V3f( -v ), IECore.V3f( v ) )
			
			def doRenderState( self, args ) :
			
				pass
					
			def doRender( self, args ) :
			
				pass
	
		node = cmds.createNode( "ieProceduralHolder" )
		fnPH = IECoreMaya.FnParameterisedHolder( str( node ) )
		
		p = TestProcedural()
		fnPH.setParameterised( p )
		
		self.assertEqual( cmds.getAttr( node + ".boundingBoxMin" ), [( -1, -1, -1 )] )
		
		plugPath = fnPH.parameterPlugPath( p["spline"] )
		plugName = plugPath.partition( "." )[2]
		pointValuePlugPath = plugPath + "[0]." + plugName + "_FloatValue"
		
		cmds.setAttr( pointValuePlugPath, 2 )
		
		self.assertEqual( cmds.getAttr( node + ".boundingBoxMin" ), [( -2, -2, -2 )] )
	
	def testObjectParameterIOProblem( self ) :
	
		fnPH = IECoreMaya.FnProceduralHolder.create( "procedural", "image", 1 )
		p = fnPH.getProcedural()
		
		w = IECore.Box2i( IECore.V2i( 0 ), IECore.V2i( 255 ) )
		image = IECore.ImagePrimitive( w, w )
		image.createFloatChannel( "Y" )
		image.createFloatChannel( "A" )
		p.parameters()["image"].setValue( image )
		fnPH.setNodeValues()
		
		cmds.file( rename = os.getcwd() + "/test/IECoreMaya/dynamicParameters.ma" )
		scene = cmds.file( force = True, type = "mayaAscii", save = True )

		cmds.file( new = True, force = True )
		cmds.file( scene, open = True )
		
		fnPH = IECoreMaya.FnProceduralHolder( "proceduralShape" )
		fnPH.setParameterisedValues()
		p = fnPH.getProcedural()
				
		i2 = p.parameters()["image"].getValue()
		
		self.assertEqual( p.parameters()["image"].getValue(), image )
			
	def tearDown( self ) :

		for f in [
			"test/IECoreMaya/reference.ma" ,
			"test/IECoreMaya/referenceMaster.ma",
			"test/IECoreMaya/dynamicParameters.ma",
			"test/IECoreMaya/imageProcedural.ma",
		] :

			if os.path.exists( f ) :

				os.remove( f )

if __name__ == "__main__":
	MayaUnitTest.TestProgram()
