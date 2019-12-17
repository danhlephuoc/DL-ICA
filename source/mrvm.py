#!C:\Users\jakob\Anaconda3\pythonw.exe
# -*- coding: utf-8 -*-

"""
FILE DESCRIPTION:

This file acts as a Java-Python "bridge". It enables a restricted usage in Python of some functionalities of the Multi Region Value Model (MRVM) imported from the Spectrum Auction Test Suite (SATS), which is written in Java.

It consists of a class called _Mrvm that has the following functionalities:
    0.CONSTRUCTOR:  __init__(self, seed, number_of_national_bidders, number_of_regional_bidders, number_of_local_bidders)
        seed = is a number for initializing the random seed generator. Note the auction instance is sampled randomly, i.e., eeach bidder's parameters, such as in which item he is interested most, is sampled randomly when creating an instance.
        number_of_national_bidders = defines the number of bidders from the type: national
        number_of_regional_bidders = defines the number of bidders from the type: regional
        number_of_local_bidders = defines the number of bidders from the type: local
        The default parametrization is: Three national bidder and four regional bidders
    1.METHOD: get_bidder_ids(self):
        Returns the bidder_ids as dict_keys.
        In the default parametrization the local bidders have id:0,1,2 and the regional bidders have ids:3,4,5,6 and the national bidders have ids:7,8,9
    2.METHOD: get_good_ids(self):
        Returns the ids of the goods as dict keys. In MRVM there are 98 items, representing the regions for the spectrum license.
    3.METHOD: calculate_value(self, bidder_id, goods_vector):
        bidder_id = unique id a bidder in the created _Mrvm instance
        goods_vector = indicator vector of the corresponding bundle for which the value should be queried (list or numpy array with dimension 98)
        Returns the (true) value of bidder bidder_id for a bundle of items goods_vector.
    4.METHOD: get_random_bids(self, bidder_id, number_of_bids, seed=None, mean_bundle_size=49, standard_deviation_bundle_size=24.5):
        bidder_id = unique id a bidder in the created _Mrvm instance
        number_of_bids = number of desired random bids
        seed = initializing the random generator for the random bids
        mean_bundle_size = mean of normal distribution. Represents the average number of 1's in the bundle vector.
        standard_deviation_bundle_size = standard deviation of normal distribution.
        This returns a list of lists of bundle-value pairs, which are sampled randomly accroding to the following procedure:
            First sample a normal random variable Z with parameters mean_bundle_size and standard_deviation_bundle_size.
            Then sample uniformly at random from all bundles in the space that contain excatly Z 1's
            (Note this sampling scheme is different from sampling uniformly at random from the bundle space. It has heavier tails, thus one obtains also samples from bundles with few and many 1's.)
    5.METHOD: get_efficient_allocation(self):
        Returns the efficient, i.e., optimal, allocation (as dict) and the corresponding social welfare (float) of the _Mrvm instance.

This class should not be called directly. Instead it should be used only via the class pysats.py. See test_javabridge.py for an example of how to use the class  _Mrvm.
"""

# Libs
from jnius import JavaClass, MetaJavaClass, JavaMethod, cast, autoclass

__author__ = 'Fabio Isler, Jakob Weissteiner'
__copyright__ = 'Copyright 2019, Deep Learning-powered Iterative Combinatorial Auctions: Jakob Weissteiner and Sven Seuken'
__license__ = 'AGPL-3.0'
__version__ = '0.1.0'
__maintainer__ = 'Jakob Weissteiner'
__email__ = 'weissteiner@ifi.uzh.ch'
__status__ = 'Dev'

# %%
SizeBasedUniqueRandomXOR = autoclass(
    'org.spectrumauctions.sats.core.bidlang.xor.SizeBasedUniqueRandomXOR')
JavaUtilRNGSupplier = autoclass(
    'org.spectrumauctions.sats.core.util.random.JavaUtilRNGSupplier')
Bundle = autoclass(
    'org.spectrumauctions.sats.core.model.Bundle')

MRVM_MIP = autoclass(
    'org.spectrumauctions.sats.opt.model.mrvm.MRVM_MIP')


class _Mrvm(JavaClass, metaclass=MetaJavaClass):
    __javaclass__ = 'org/spectrumauctions/sats/core/model/mrvm/MultiRegionModel'

    # TODO: I don't find a way to have the more direct accessors of the DefaultModel class. So for now, I'm mirroring the accessors
    #createNewPopulation = JavaMultipleMethod([
    #    '()Ljava/util/List;',
    #    '(J)Ljava/util/List;'])
    setNumberOfNationalBidders = JavaMethod('(I)V')
    setNumberOfRegionalBidders = JavaMethod('(I)V')
    setNumberOfLocalBidders = JavaMethod('(I)V')
    createWorld = JavaMethod(
        '(Lorg/spectrumauctions/sats/core/util/random/RNGSupplier;)Lorg/spectrumauctions/sats/core/model/mrvm/MRVMWorld;')
    createPopulation = JavaMethod(
        '(Lorg/spectrumauctions/sats/core/model/World;Lorg/spectrumauctions/sats/core/util/random/RNGSupplier;)Ljava/util/List;')

    population = {}
    goods = {}
    efficient_allocation = None

    def __init__(self, seed, number_of_national_bidders, number_of_regional_bidders, number_of_local_bidders):
        super().__init__()
        if seed:
            rng = JavaUtilRNGSupplier(seed)
        else:
            rng = JavaUtilRNGSupplier()

        self.setNumberOfNationalBidders(number_of_national_bidders)
        self.setNumberOfRegionalBidders(number_of_regional_bidders)
        self.setNumberOfLocalBidders(number_of_local_bidders)

        world = self.createWorld(rng)
        self._bidder_list = self.createPopulation(world, rng)

        # Store bidders
        bidderator = self._bidder_list.iterator()
        while bidderator.hasNext():
            bidder = bidderator.next()
            self.population[bidder.getId()] = bidder

        # Store goods
        goods_iterator = self._bidder_list.iterator().next().getWorld().getLicenses().iterator()
        while goods_iterator.hasNext():
            good = goods_iterator.next()
            self.goods[good.getId()] = good

        self.goods = list(map(lambda _id: self.goods[_id], sorted(self.goods.keys())))

    def get_bidder_ids(self):
        return self.population.keys()

    def get_good_ids(self):
        return dict.fromkeys(list(range(98))).keys()

    def calculate_value(self, bidder_id, goods_vector):
        assert len(goods_vector) == len(self.goods)
        bidder = self.population[bidder_id]
        bundle = Bundle()
        for i in range(len(goods_vector)):
            if goods_vector[i] == 1:
                bundle.add(self.goods[i])
        return bidder.calculateValue(bundle).doubleValue()

    def get_random_bids(self, bidder_id, number_of_bids, seed=None, mean_bundle_size=49, standard_deviation_bundle_size=24.5):
        bidder = self.population[bidder_id]
        if seed:
            rng = JavaUtilRNGSupplier(seed)
        else:
            rng = JavaUtilRNGSupplier()
        valueFunction = cast('org.spectrumauctions.sats.core.bidlang.xor.SizeBasedUniqueRandomXOR',
                             bidder.getValueFunction(SizeBasedUniqueRandomXOR, rng))
        valueFunction.setDistribution(
            mean_bundle_size, standard_deviation_bundle_size)
        valueFunction.setIterations(number_of_bids)
        xorBidIterator = valueFunction.iterator()
        bids = []
        while (xorBidIterator.hasNext()):
            xorBid = xorBidIterator.next()
            bid = []
            for i in range(len(self.goods)):
                if (xorBid.getLicenses().contains(self.goods[i])):
                    bid.append(1)
                else:
                    bid.append(0)
            bid.append(xorBid.value)
            bids.append(bid)
        return bids

    def get_efficient_allocation(self):
        if self.efficient_allocation:
            return self.efficient_allocation, sum([self.efficient_allocation[bidder_id]['value'] for bidder_id in self.efficient_allocation.keys()])

        mip = MRVM_MIP(self._bidder_list)
        mip.setDisplayOutput(True)

        generic_allocation = cast(
            'org.spectrumauctions.sats.opt.domain.GenericAllocation', mip.calculateAllocation())

        self.efficient_allocation = {}

        for bidder_id, bidder in self.population.items():
            self.efficient_allocation[bidder_id] = {}
            self.efficient_allocation[bidder_id]['good_ids'] = []
            if generic_allocation.getWinners().contains(bidder):
                bidder_allocation = generic_allocation.getAllocation(bidder)
                good_iterator = bidder_allocation.iterator()
                while good_iterator.hasNext():
                    self.efficient_allocation[bidder_id]['good_ids'].append(good_iterator.next().getId())

            self.efficient_allocation[bidder_id]['value'] = generic_allocation.getTradeValue(
                bidder).doubleValue()

        return self.efficient_allocation, generic_allocation.totalValue.doubleValue()
