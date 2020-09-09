#
# This file is part of ap_pipe.
#
# Developed for the LSST Data Management System.
# This product includes software developed by the LSST Project
# (http://www.lsst.org).
# See the COPYRIGHT file at the top-level directory of this distribution
# for details of code ownership.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import numpy as np
import unittest

import lsst.geom as geom
import lsst.skymap as skyMap
import lsst.utils.tests

from lsst.ap.pipe.createApFakes import CreateRandomApFakesTask, CreateRandomApFakesConfig


class TestCreateApFakes(lsst.utils.tests.TestCase):

    def setUp(self):
        """
        """
        simpleMapConfig = skyMap.discreteSkyMap.DiscreteSkyMapConfig()
        simpleMapConfig.raList = [10]
        simpleMapConfig.decList = [-1]
        simpleMapConfig.radiusList = [0.1]

        self.simpleMap = skyMap.DiscreteSkyMap(simpleMapConfig)
        self.tractId = 0
        bCircle = self.simpleMap.generateTract(self.tractId).getInnerSkyPolygon().getBoundingCircle()
        self.nSources = 10
        self.sourceDensity = (self.nSources
                              / (bCircle.getArea() * (180 / np.pi) ** 2))
        self.fraction = 0.5
        self.nInVisit = (int(self.nSources * self.fraction)
                         + int((1 - self.fraction) / 2 * self.nSources))
        self.nInTemplate = (self.nSources - self.nInVisit
                            + int(self.nSources * self.fraction))
        self.rng = np.random.default_rng(1234)

    def testRun(self):
        """Test the run method.
        """
        fakesConfig = CreateRandomApFakesConfig()
        fakesConfig.fraction = 0.5
        fakesConfig.fakeDensity = self.sourceDensity
        fakesTask = CreateRandomApFakesTask(config=fakesConfig)
        bCircle = self.simpleMap.generateTract(self.tractId).getInnerSkyPolygon().getBoundingCircle()
        result = fakesTask.run(self.tractId, self.simpleMap)
        fakeCat = result.fakeCat.toDataFrame()
        self.assertEqual(len(fakeCat), self.nSources)
        for idx, row in fakeCat.iterrows():
            self.assertTrue(
                bCircle.contains(
                    geom.SpherePoint(row[fakesTask.config.raColName],
                                     row[fakesTask.config.decColName],
                                     geom.radians).getVector()))
        self.assertEqual(fakeCat[fakesConfig.visitSourceFlagCol].sum(),
                         self.nInVisit)
        self.assertEqual(fakeCat[fakesConfig.templateSourceFlagCol].sum(),
                         self.nInTemplate)
        for f in fakesConfig.filterSet:
            filterMags = fakeCat[fakesConfig.magVar % f]
            self.assertEqual(self.nSources, len(filterMags))
            self.assertTrue(
                np.all(fakesConfig.magMin <= filterMags))
            self.assertTrue(
                np.all(fakesConfig.magMax > filterMags))

    def testCreateRandomPositions(self):
        """Test that the correct number of sources are produced and are
        contained in the cap bound.
        """
        fakesTask = CreateRandomApFakesTask()
        bCircle = self.simpleMap.generateTract(self.tractId).getInnerSkyPolygon().getBoundingCircle()

        randData = fakesTask.createRandomPositions(
            nFakes=self.nSources,
            boundingCircle=bCircle,
            rng=self.rng)
        self.assertEqual(self.nSources, len(randData[fakesTask.config.raColName]))
        self.assertEqual(self.nSources, len(randData[fakesTask.config.decColName]))
        for idx in range(self.nSources):
            self.assertTrue(
                bCircle.contains(
                    geom.SpherePoint(randData[fakesTask.config.raColName][idx],
                                     randData[fakesTask.config.decColName][idx],
                                     geom.radians).getVector()))

    def testCreateRotMatrix(self):
        """Test that the rotation matrix is computed correctly and rotates
        a test vector to the expected location.
        """
        createFakes = CreateRandomApFakesTask()
        bCircle = self.simpleMap.generateTract(self.tractId).getInnerSkyPolygon().getBoundingCircle()
        rotMatrix = createFakes._createRotMatrix(bCircle)
        rotatedVector = np.dot(rotMatrix, np.array([0, 0, 1]))
        expectedVect = bCircle.getCenter()
        self.assertAlmostEqual(expectedVect.x(), rotatedVector[0])
        self.assertAlmostEqual(expectedVect.y(), rotatedVector[1])
        self.assertAlmostEqual(expectedVect.z(), rotatedVector[2])

    def testVisitCoaddSubdivision(self):
        """Test that the number of assigned visit to template objects is
        correct.
        """
        fakesConfig = CreateRandomApFakesConfig()
        fakesConfig.fraction = 0.5
        fakesTask = CreateRandomApFakesTask(config=fakesConfig)
        subdivision = fakesTask.createVisitCoaddSubdivision(self.nSources)
        self.assertEqual(
            subdivision[fakesConfig.visitSourceFlagCol].sum(),
            self.nInVisit)
        self.assertEqual(
            subdivision[fakesConfig.templateSourceFlagCol].sum(),
            self.nInTemplate)

    def testRandomMagnitudes(self):
        """Test that the correct number of filters and magnitudes have been
        produced.
        """
        fakesConfig = CreateRandomApFakesConfig()
        fakesConfig.filterSet = ["u", "g"]
        fakesConfig.magVar = "%smag"
        fakesConfig.magMin = 20
        fakesConfig.magMax = 21
        fakesTask = CreateRandomApFakesTask(config=fakesConfig)
        mags = fakesTask.createRandomMagnitudes(self.nSources, self.rng)
        self.assertEqual(len(fakesConfig.filterSet), len(mags))
        for f in fakesConfig.filterSet:
            filterMags = mags[fakesConfig.magVar % f]
            self.assertEqual(self.nSources, len(filterMags))
            self.assertTrue(
                np.all(fakesConfig.magMin <= filterMags))
            self.assertTrue(
                np.all(fakesConfig.magMax > filterMags))


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()