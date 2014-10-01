# hand rolled ghetto chord similarity measure gives us a similarity matrix
# assumptions: 
# all notes are harmonically truncated saw waves
# all harmonics wrapped to the octave

# can construct a similarity by the inner product based on inner product of the the kernel-approximated vectors, then measuring ratio to mean inner norm; this is more-or-less the covariance of spectral energy
# also could track kernel width per-harmonic; is this principled? "feels" right, but we'll see.
# Could do a straight nearness search off the distance matrix using ball tree (4000 is not so many points; brute force also OK)
# or cast to a basis of notes using a custom kernel
# need to have this in terms of notes, though
# TODO: weight by actual chord occurence (when do 11 notes play at once? even 6 is pushing it)
# TODO: toroidal maps
# TODO: simple transition graph might work, if it was made regular in some way
# TODO: we could even place chords on a grid in a way that provides minimal dissonance between them; esp since we may repeat chords if necessary. In fact, we could even construct such a path by weaving chords together. Hard to navigate, though.
# TODO: segment on number of notes, either before or after MDS
# TODO: segment on total spectral energy; or at least weight transitions on relative energy. (how often do we then increase energy?)
# TODO: colorize base on number of notes
# TODO: ditch python dict serialization in favour of indexed pytables
# TODO: Actually integrate kernels together
# TODO: ditch pickle for optimized tables https://pytables.github.io/usersguide/optimization.html
# TODO: really need to be preserving the seed for this stuff
# TODO: We could use this by constructing 8 2d navigation systems, and for each point, the 7 nearest neighbours in adjacent leaves
# TODO: Or can i just pull out one of these leaves and inspect for what it is?
# TODO: MIDI version
# TODO: straight number-of-notes colour map
# TODO: For more than ca 6 notes, this is nonsense; we don't care about such "chords"

import numpy as np
from scipy.spatial.distance import squareform, pdist
from math import sqrt
import tables
import gzip
import cPickle as pickle
from sklearn.manifold import MDS
from sklearn.decomposition import PCA, KernelPCA
import os.path
from sklearn.cluster import SpectralClustering
from chordmap_base import *
import chordmap_vis
from sklearn.covariance import EllipticEnvelope

N_HARMONICS = 16
KERNEL_WIDTH = 0.01 # less than this and they are the same note (probably too wide)

chords_i_products = None
chords_i_products_square = None
chords_i_dists_square = None
chords_i_dists = None

energies = 1.0/(np.arange(N_HARMONICS)+1)
base_energies = 1.0/(np.arange(N_HARMONICS)+1)
base_harm_fs = np.arange(N_HARMONICS)+1
base_fundamentals = 2.0**(np.arange(12)/12.0)
# wrap harmonics
note_harmonics = (((np.outer(base_fundamentals, base_harm_fs)-1.0)%1.0)+1)
# Alternatively (Thanks James Nichols for noticing)
# note_harmonics = 2.0 ** (np.log2(np.outer(base_fundamentals, base_harm_fs))%1.0)

note_idx = np.arange(12, dtype="uint32")
harm_idx = np.arange(N_HARMONICS)
cross_harm_idx = cross_p_idx(N_HARMONICS, N_HARMONICS)
chord_idx = np.arange(2**12).reshape(2**12,1)

def binrotate(i, steps=1, lgth=12):
    "convenient to pack note strings to ints for performance"
    binrep = bin(i)[2:]
    pad_digits = lgth-len(binrep)
    binrep = "0"*pad_digits + binrep
    binrep = binrep[steps:]+binrep[0:steps]
    return int(binrep, base=2)

def v_kernel_fn(f1, f2, a1, a2, widths=0.01):
    """
    returns rect kernel product of points [f1, a1, f2, a2]
    NB this is not actually a cyclic kernel on [1,2], though the difference is small
    """
    return (np.abs(f1-f2)<widths)*a1*a2

def chord_notes_from_ind(i):
    return np.asarray(np.nonzero(bit_unpack(i))[0], dtype="uint")
def chord_ind_from_notes(i):
    return np.asarray(np.nonzero(bit_unpack(i))[0], dtype="uint")
def chord_mask_from_ind(i):
    return np.asarray(np.nonzero(bit_unpack(i))[0], dtype="uint")
def chord_mask_from_notes(i):
    return np.asarray(np.nonzero(bit_unpack(i))[0], dtype="uint")

def make_chord(notes):
    notes = tuple(sorted(notes))
    if not notes in _make_chord_cache:
        chord_harm_fs = note_harmonics[notes,:].flatten()
        chord_harm_energies = np.tile(base_energies, len(notes))
        _make_chord_cache[notes] = np.vstack([
            chord_harm_fs, chord_harm_energies
        ])
    return _make_chord_cache[notes]
if "_make_chord_cache" not in globals():
    if os.path.exists('_chord_map_cache_make_chords.gz'): 
        with gzip.open('_chord_map_cache_make_chords.gz', 'rb') as f:
            _make_chord_cache = pickle.load(f)
    else:
        _make_chord_cache = {}

def v_chord_product(c1, c2):
    idx = cross_p_idx(c1.shape[1], c2.shape[1])
    if idx.size==0:
        return 0.0
    f1 = c1[0,idx[0]]
    f2 = c2[0,idx[1]]
    a1 = c1[1,idx[0]]
    a2 = c2[1,idx[1]]
    return v_kernel_fn(f1, f2, a1, a2).sum()

def v_chord_dist(c1, c2):
    "construct a chord distance from the chord inner product"
    return sqrt(
        v_chord_product(c1, c1)
        - 2 * v_chord_product(c1, c2)
        + v_chord_product(c2, c2)
    )
    
def v_chord_product_from_chord_i_raw(ci1, ci2):
    """uncached version"""
    ci1 = int(ci1)
    ci2 = int(ci2)
    return v_chord_product(
        make_chord(chord_notes_from_ind(ci1)),
        make_chord(chord_notes_from_ind(ci2))
    )

def v_chord_product_from_chord_i_raw(ci1, ci2):
    """uncached version, for filling the cache with."""
    ci1 = int(ci1)
    ci2 = int(ci2)
    return v_chord_product(
        make_chord(chord_notes_from_ind(ci1)),
        make_chord(chord_notes_from_ind(ci2))
    )

def v_chord_product_from_chord_i_raw(ci1, ci2):
    """cached version"""
    ci1 = int(ci1)
    ci2 = int(ci2)
    return chords_i_products_square[int(ci1), int(ci2)]
    
def v_chord_dist2_from_chord_i(ci1, ci2):
    "construct a chord distance^2 from the chord inner product"
    #this is just to calculate how often to print progress messages
    v_chord_dist2_from_chord_i.callct = v_chord_dist2_from_chord_i.callct + 1
    if (v_chord_dist2_from_chord_i.callct % 11==0):
        print ci1, ci2
    return (
        v_chord_product_from_chord_i(ci1, ci1)
        - 2 * v_chord_product_from_chord_i(ci1, ci2)
        + v_chord_product_from_chord_i(ci2, ci2)
    )
v_chord_dist2_from_chord_i.callct = 0

if os.path.exists("dists.h5"):
    with tables.open_file("dists.h5", 'r') as handle:
        chords_i_products = handle.get_node("/", 'v_products').read()
        chords_i_products_square = handle.get_node("/", 'v_sq_products').read()
        chords_i_dists = handle.get_node("/", 'v_dists').read()
        chords_i_dists_square = handle.get_node("/", 'v_sq_dists').read()
else:
    chords_i_products = pdist(
        np.arange(2**12).reshape(2**12,1),
        v_chord_product_from_chord_i
    )
    chords_i_products_square = squareform(chords_i_products)
    chords_i_dists = np.sqrt(pdist(
        chord_idx,
        v_chord_dist2_from_chord_i
    ))
    chords_i_dists_square = squareform(chords_i_dists)

if not os.path.exists("dists.h5"):
    with tables.open_file("dists.h5", 'w') as handle:
        data_atom_type = tables.Float32Atom()
        filt=tables.Filters(complevel=5, complib='blosc')
        handle.create_carray("/",'v_dists',
            atom=data_atom_type, shape=chords_i_dists.shape,
            title="dists",
            filters=filt)[:] = chords_i_dists
        handle.create_carray("/",'v_sq_dists',
            atom=data_atom_type, shape=chords_i_dists_square.shape,
            title="sq dists",
            filters=filt)[:] = chords_i_dists_square
        handle.create_carray("/",'v_products',
            atom=data_atom_type, shape=chords_i_products.shape,
            title="product",
            filters=filt)[:] = chords_i_products
        handle.create_carray("/",'v_sq_products',
            atom=data_atom_type, shape=chords_i_products_square.shape,
            title="sq products",
            filters=filt)[:] = chords_i_products_square

if not os.path.exists('_chord_map_cache_products.gz'):
    #this pickle is incredibly huge; dunno why
    # should truncate the floats
    with gzip.open('_chord_map_cache_products.gz', 'wb') as f:
        pickle.dump(_v_chord_product_from_chord_i_cache, f, protocol=2)
if not os.path.exists('_chord_map_cache_make_chords.gz'):
    #this one is tiny (probably because repeated floats more compressible)
    with gzip.open('_chord_map_cache_make_chords.gz', 'wb') as f:
        pickle.dump(_make_chord_cache, f, protocol=2)

def get_pca(sq_dists, n_dims=None):
    transformer = KernelPCA(n_components=n_dims, kernel='precomputed', eigen_solver='auto', tol=0, max_iter=None)
    transformed = transformer.fit_transform(sq_dists) #feed the product matric directly in for precomputed case
    return transformed

def get_mds(sq_dists, n_dims=3, metric=True, rotate=True):
    transformer = MDS(n_components=n_dims, metric=metric, n_init=4, max_iter=300, verbose=1, eps=0.001, n_jobs=3, random_state=None, dissimilarity='precomputed')
    transformed = transformer.fit_transform(sq_dists)
    if rotate:
        # Rotate the data to a hopefully consistent orientation
        clf = PCA(n_components=n_dims)
        transformed = clf.fit_transform(transformed)
    return transformed



lin_mds_3 = get_mds(chords_i_dists_square, 3, rotate=False)
dump_projection("lin_mds_3.h5", lin_mds_3)
clusters = SpectralClustering(n_clusters=12, random_state=None, n_init=16, gamma=16.0, affinity='rbf', n_neighbors=10, assign_labels='kmeans').fit_predict(lin_mds_3)
centers = np.array([lin_mds_3[clusters==i].mean(0) for i in xrange(8)])
most_central = (centers**2).sum(1).argmin()
fave_cluster = lin_mds_3[clusters==most_central]
envelope = EllipticEnvelope(contamination=0.02)
envelope.fit(fave_cluster)
fave_cluster_best_points = fave_cluster[(envelope.predict(fave_cluster)==1).nonzero()[0]]
fave_cluster_ids = (clusters==most_central).nonzero()[0]
anal3 = PCA(n_components=3)
anal3.fit(fave_cluster_best_points)
lin_mds_3_rot = anal3.transform(lin_mds_3)
chordmap_vis.plot_3d(lin_mds_3_rot, clusters)
# can now PCA each group down to 2 elems
anal2 = PCA(n_components=2)
anal2.fit(fave_cluster_best_points)
leaf_1=anal2.transform(fave_cluster) # or this could be an MDS again, from original distances (be careful orchestrating lookups of lookups)

nonlin_mds_3 = get_mds(chords_i_dists_square, 3, metric=False, rotate=False) 
dump_projection("nonlin_mds_3.h5", nonlin_mds_3)
nonlin_clusters = SpectralClustering(n_clusters=12, random_state=None, n_init=16, gamma=16.0, affinity='rbf', n_neighbors=10, assign_labels='kmeans').fit_predict(nonlin_mds_3)
nonlin_centers = np.array([nonlin_mds_3[clusters==i].mean(0) for i in xrange(12)])
chordmap_vis.plot_3d(nonlin_mds_3, nonlin_clusters)
